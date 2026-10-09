import React from 'react';
import {Composition, getInputProps, registerRoot} from 'remotion';
import {Invitation, type InvitationProps} from './Invitation';

const Root: React.FC = () => {
  const props = getInputProps() as unknown as InvitationProps;
  return <Composition id="HermesInvitation" component={Invitation} width={props.width}
    height={props.height} fps={props.fps} durationInFrames={props.fps * props.duration_seconds}
    defaultProps={props}/>;
};

registerRoot(Root);
