"""Rebuildable, bounded index over ArtifactStore and journal sample refs."""
from .models import TransitionSample
from itertools import islice


class ExperienceCorpus:
    def __init__(self, artifacts, refs=(), *, max_samples=4096, discover=False):
        self.artifacts = artifacts
        self.max_samples = max_samples
        self.refs = list(dict.fromkeys(refs))[-max_samples:]
        if discover:
            # Existing content-addressed artifacts are the index source. No new DB.
            for directory in islice(artifacts.root.iterdir(), 1024):
                if directory.is_dir():
                    for path in islice(directory.glob('transition_*.json'), max_samples * 2):
                        if path.name.endswith('.meta.json'):
                            continue
                        ref = f'artifact://tasks/{directory.name}/{path.name}'
                        if ref not in self.refs:
                            self.refs.append(ref)
            self.refs = self.refs[-max_samples:]

    def capture(self, sample):
        body = sample.to_dict()
        from workstation.recipes import digest
        ref = self.artifacts.store(sample.provenance.task_id or 'experience',
            body['sample_id'] + '_' + digest(body)[:24] + '.json', body, schema='hermes.transition_sample.v1').ref
        if ref not in self.refs:
            self.refs.append(ref)
            self.refs = self.refs[-self.max_samples:]
        return ref

    def ingest_journal(self, journal):
        for event in journal.read_events():
            ref = event.metadata.get('transition_ref')
            if ref and ref not in self.refs:
                self.refs.append(ref)
        self.refs = self.refs[-self.max_samples:]

    def accept_run(self, journal, outcome):
        """Project accepted final readback; acceptance never elevates E strength."""
        from .models import TransitionOutcome, Verification
        self.ingest_journal(journal)
        candidates = self.query(task_id=outcome.task_id, run_id=outcome.run_id)
        if not candidates or outcome.status.value != 'verified_completed' or outcome.uncertain_mutation:
            return None
        last = candidates[-1]
        refs = {r.uri for r in outcome.evidence_refs}
        # Only observations actually linked by acceptance verifier evidence close a segment.
        valid_refs = {v.get('evidence_ref') for v in outcome.verifier_results if v.get('passed') is True}
        if last.state_after.artifact_ref not in refs & valid_refs:
            return None
        last.outcome = TransitionOutcome.VERIFIED_SUCCESS
        last.verification = Verification(last.verification.evidence_strength, 'canonical_acceptance_readback',
            last.state_after.semantic_predicates, sorted(refs & valid_refs))
        ref = self.capture(last)
        journal.record(__import__('workstation.contracts', fromlist=['ExecutionEventKind']).ExecutionEventKind.ACTION,
            'accepted transition projected; promotion admission remains independent',
            metadata={'transition_ref': ref, 'run_id': outcome.run_id})
        return ref

    def query(self, **dimensions):
        observations = {}
        for ref in self.refs:
            sample = TransitionSample.from_dict(self.artifacts.read_json(ref))
            sample.provenance.sample_ref = ref
            dims = {'route': sample.operation.canonical_route, 'runtime': sample.provenance.runtime,
                'operation_family': sample.operation.operation_family, 'target_family': sample.operation.target_family,
                'effect': sample.operation.effect_class, 'scope': sample.operation.scope,
                'outcome': sample.outcome.value, 'trust_class': sample.provenance.trust_class,
                'run_id': sample.provenance.run_id, 'task_id': sample.provenance.task_id}
            key = (sample.provenance.task_id, sample.provenance.run_id, sample.provenance.operation_id or ref)
            previous = observations.get(key)
            if previous is None or previous[0].outcome.value != 'verified_success' or sample.outcome.value == 'verified_success':
                observations[key] = (sample, dims)
        result = [s for s, dims in observations.values() if all(dims.get(k) == v for k, v in dimensions.items())]
        if result and all(s.provenance.operation_index is not None for s in result):
            result.sort(key=lambda s: (s.provenance.task_id or '', s.provenance.run_id or '', s.provenance.operation_index))
        return result

    def traces(self, **dimensions):
        groups = {}
        for sample in self.query(**dimensions):
            groups.setdefault((sample.provenance.task_id, sample.provenance.run_id), []).append(sample)
        return list(groups.values())
