import { useMemo } from 'react';
import { positionToFill } from '../utils/colorScale';

// Formation position maps — [x%, y%] on pitch (0,0=top-left, 100,100=bottom-right)
// Values are for HOME team (top-down view). Away team is mirrored vertically.
const FORMATIONS = {
  '4-4-2': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'RB',  x: 85, y: 75 }, { pos: 'CB',  x: 62, y: 75 },
      { pos: 'CB',  x: 38, y: 75 }, { pos: 'LB',  x: 15, y: 75 },
      { pos: 'RM',  x: 85, y: 52 }, { pos: 'CM',  x: 62, y: 52 },
      { pos: 'CM',  x: 38, y: 52 }, { pos: 'LM',  x: 15, y: 52 },
      { pos: 'ST',  x: 62, y: 20 }, { pos: 'ST',  x: 38, y: 20 },
    ],
    label: '4-4-2',
  },
  '4-3-3': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'RB',  x: 85, y: 75 }, { pos: 'CB',  x: 62, y: 75 },
      { pos: 'CB',  x: 38, y: 75 }, { pos: 'LB',  x: 15, y: 75 },
      { pos: 'CM',  x: 70, y: 55 }, { pos: 'CDM', x: 50, y: 58 }, { pos: 'CM',  x: 30, y: 55 },
      { pos: 'RW',  x: 82, y: 22 }, { pos: 'ST',  x: 50, y: 15 }, { pos: 'LW',  x: 18, y: 22 },
    ],
    label: '4-3-3',
  },
  '3-5-2': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'CB',  x: 70, y: 76 }, { pos: 'CB',  x: 50, y: 78 }, { pos: 'CB',  x: 30, y: 76 },
      { pos: 'RM',  x: 90, y: 55 }, { pos: 'CM',  x: 68, y: 52 }, { pos: 'CDM', x: 50, y: 55 },
      { pos: 'CM',  x: 32, y: 52 }, { pos: 'LM',  x: 10, y: 55 },
      { pos: 'ST',  x: 62, y: 20 }, { pos: 'ST',  x: 38, y: 20 },
    ],
    label: '3-5-2',
  },
  '4-2-3-1': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'RB',  x: 85, y: 76 }, { pos: 'CB',  x: 62, y: 76 },
      { pos: 'CB',  x: 38, y: 76 }, { pos: 'LB',  x: 15, y: 76 },
      { pos: 'CDM', x: 62, y: 60 }, { pos: 'CDM', x: 38, y: 60 },
      { pos: 'RW',  x: 80, y: 36 }, { pos: 'CAM', x: 50, y: 36 }, { pos: 'LW',  x: 20, y: 36 },
      { pos: 'ST',  x: 50, y: 14 },
    ],
    label: '4-2-3-1',
  },
  '5-3-2': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'RWB', x: 92, y: 70 }, { pos: 'CB',  x: 70, y: 76 }, { pos: 'CB',  x: 50, y: 78 },
      { pos: 'CB',  x: 30, y: 76 }, { pos: 'LWB', x: 8,  y: 70 },
      { pos: 'CM',  x: 68, y: 50 }, { pos: 'CDM', x: 50, y: 52 }, { pos: 'CM',  x: 32, y: 50 },
      { pos: 'ST',  x: 62, y: 20 }, { pos: 'ST',  x: 38, y: 20 },
    ],
    label: '5-3-2',
  },
  '4-1-4-1': {
    positions: [
      { pos: 'GK',  x: 50, y: 92 },
      { pos: 'RB',  x: 85, y: 76 }, { pos: 'CB',  x: 62, y: 76 },
      { pos: 'CB',  x: 38, y: 76 }, { pos: 'LB',  x: 15, y: 76 },
      { pos: 'CDM', x: 50, y: 62 },
      { pos: 'RM',  x: 85, y: 44 }, { pos: 'CM',  x: 62, y: 44 },
      { pos: 'CM',  x: 38, y: 44 }, { pos: 'LM',  x: 15, y: 44 },
      { pos: 'ST',  x: 50, y: 14 },
    ],
    label: '4-1-4-1',
  },
};

const PITCH_W = 300;
const PITCH_H = 440;

function PlayerNode({ player, index, isAway, onClick }) {
  const fill = positionToFill(player.position);
  const px = isAway
    ? (PITCH_W * (100 - player.x)) / 100
    : (PITCH_W * player.x) / 100;
  const py = isAway
    ? (PITCH_H * (100 - player.y)) / 100
    : (PITCH_H * player.y) / 100;

  return (
    <g
      className="pitch-player"
      onClick={() => onClick && onClick(index)}
      style={{ cursor: 'pointer' }}
    >
      <circle cx={px} cy={py} r={14} fill={fill} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
      <circle cx={px} cy={py} r={13} fill="none" stroke={fill} strokeWidth={1} strokeOpacity={0.4} />
      <text
        x={px}
        y={py - 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="9"
        fontWeight="700"
        fill="#fff"
      >
        {player.jersey_no || (index + 1)}
      </text>
      {player.name && (
        <text
          x={px}
          y={py + 18}
          textAnchor="middle"
          fontSize="7.5"
          fontWeight="600"
          fill="rgba(255,255,255,0.85)"
        >
          {player.name.split(' ').pop()?.slice(0, 8) || ''}
        </text>
      )}
    </g>
  );
}

export default function PitchFormation({ players = [], formation = '4-4-2', isAway = false }) {
  const formationData = FORMATIONS[formation] || FORMATIONS['4-4-2'];

  // Merge formation positions with player data
  const positioned = useMemo(() => {
    return formationData.positions.map((pos, i) => ({
      ...pos,
      ...(players[i] || {}),
      position: (players[i]?.position) || pos.pos,
    }));
  }, [formationData, players]);

  return (
    <div className="relative w-full" style={{ maxWidth: PITCH_W }}>
      <svg
        viewBox={`0 0 ${PITCH_W} ${PITCH_H}`}
        className="w-full rounded-xl overflow-hidden"
        style={{ background: 'linear-gradient(175deg, #1a4d2e 0%, #0f3820 50%, #1a4d2e 100%)' }}
      >
        {/* Pitch markings */}
        <PitchMarkings />

        {/* Player nodes */}
        {positioned.map((p, i) => (
          <PlayerNode key={i} player={p} index={i} isAway={isAway} />
        ))}
      </svg>
    </div>
  );
}

function PitchMarkings() {
  const W = PITCH_W, H = PITCH_H;
  const stroke = 'rgba(255,255,255,0.35)';
  const sw = 1.2;
  return (
    <g fill="none" stroke={stroke} strokeWidth={sw}>
      {/* Outer boundary */}
      <rect x={12} y={12} width={W - 24} height={H - 24} rx={2} />
      {/* Center line */}
      <line x1={12} y1={H / 2} x2={W - 12} y2={H / 2} />
      {/* Center circle */}
      <circle cx={W / 2} cy={H / 2} r={40} />
      {/* Center spot */}
      <circle cx={W / 2} cy={H / 2} r={2} fill={stroke} />
      {/* Top penalty area */}
      <rect x={W * 0.18} y={12} width={W * 0.64} height={H * 0.16} />
      {/* Top 6-yard box */}
      <rect x={W * 0.31} y={12} width={W * 0.38} height={H * 0.06} />
      {/* Top penalty spot */}
      <circle cx={W / 2} cy={H * 0.13} r={1.5} fill={stroke} />
      {/* Top penalty arc */}
      <path d={`M ${W * 0.3} ${H * 0.165} Q ${W * 0.5} ${H * 0.21} ${W * 0.7} ${H * 0.165}`} strokeDasharray="4 2" />
      {/* Bottom penalty area */}
      <rect x={W * 0.18} y={H - 12 - H * 0.16} width={W * 0.64} height={H * 0.16} />
      {/* Bottom 6-yard box */}
      <rect x={W * 0.31} y={H - 12 - H * 0.06} width={W * 0.38} height={H * 0.06} />
      {/* Bottom penalty spot */}
      <circle cx={W / 2} cy={H * 0.87} r={1.5} fill={stroke} />
      {/* Bottom penalty arc */}
      <path d={`M ${W * 0.3} ${H * 0.835} Q ${W * 0.5} ${H * 0.79} ${W * 0.7} ${H * 0.835}`} strokeDasharray="4 2" />
      {/* Top goal */}
      <rect x={W * 0.38} y={10} width={W * 0.24} height={6} fill="rgba(255,255,255,0.15)" />
      {/* Bottom goal */}
      <rect x={W * 0.38} y={H - 16} width={W * 0.24} height={6} fill="rgba(255,255,255,0.15)" />
    </g>
  );
}
