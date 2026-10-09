import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export interface InvitationProps {
  title: string;
  subtitle: string;
  footer: string;
  background: string;
  foreground: string;
  accent: string;
  width: number;
  height: number;
  fps: number;
  duration_seconds: number;
  logo_radius: number;
}

export const Invitation: React.FC<InvitationProps> = (props) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = interpolate(frame, [0, fps], [0, 1], {extrapolateRight: 'clamp'});
  const pulse = 1 + Math.sin(frame / fps * Math.PI) * 0.04;
  return <AbsoluteFill style={{backgroundColor: props.background, color: props.foreground,
    fontFamily: 'Arial, sans-serif', alignItems: 'center', justifyContent: 'center'}}>
    <svg width={props.width} height={props.height} viewBox="0 0 360 640"
      style={{position: 'absolute', inset: 0}}>
      <circle cx={180} cy={130} r={props.logo_radius} fill={props.accent}
        opacity={entrance} transform={`translate(180 130) scale(${pulse}) translate(-180 -130)`}/>
      <rect x={28} y={240} width={304} height={230} rx={16} fill={props.foreground} opacity={0.07}/>
    </svg>
    <div style={{position: 'absolute', top: '42%', width: '84%', textAlign: 'center',
      opacity: entrance, transform: `translateY(${(1 - entrance) * 24}px)`}}>
      <div style={{fontSize: props.width * 0.08, overflowWrap: 'anywhere'}}>{props.title}</div>
      <div style={{fontSize: props.width * 0.06, color: props.accent, marginTop: 28,
        overflowWrap: 'anywhere'}}>{props.subtitle}</div>
      <div style={{fontSize: props.width * 0.047, marginTop: 30,
        overflowWrap: 'anywhere'}}>{props.footer}</div>
    </div>
  </AbsoluteFill>;
};
