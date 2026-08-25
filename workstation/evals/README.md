# Browser evals

The eval harness compares three Workstation execution modes without conflating
their intended use cases:

| Mode | Primary use | Persistent auth | Visible | Adaptive code |
|---|---|---:|---:|---:|
| internal | personal/authenticated Workstation browser | yes | yes | CDP controller |
| agent-browser | public/local deterministic browser work | optional | optional | no |
| browser-exec | complex/adaptive Power Mode | configurable | optional | yes |

Initial metrics:
- task success
- retries/recovery
- wall time
- input/output tokens
- cost
- action count
- final-state correctness
- transactional duplicates
- background survival
- profile persistence
- crash recovery

Reference suites: BrowseWebApp Bench and BrowserTransactionBench. We do not
vendor their datasets in this patch.
