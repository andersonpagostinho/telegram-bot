/**
 * AgentEdge - React Flow edge component for agent relationships
 * Shows connections between agents (delegation/dependency)
 * Animation only on active events
 */

import React from 'react';
import {
  EdgeProps,
  getBezierPath,
  BaseEdge,
  EdgeLabelRenderer,
} from 'reactflow';
import { theme } from '../../lib/theme/tokens';

interface AgentEdgeData {
  isActive?: boolean;
  label?: string;
}

type AgentEdgeProps = EdgeProps<AgentEdgeData>;

export const AgentEdge: React.FC<AgentEdgeProps> = ({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isActive = data?.isActive ?? false;

  const strokeColor = selected
    ? theme.colors.semantic.agentAnalyzing
    : isActive
      ? theme.colors.semantic.agentWorking
      : theme.colors.baseline.border;

  const strokeWidth = selected ? 2 : isActive ? 1.5 : 1;

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: strokeColor,
          strokeWidth,
          transition: 'all 0.3s ease',
          opacity: isActive ? 1 : 0.6,
          animation: isActive ? 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
        }}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              fontSize: '0.65rem',
              color: theme.colors.baseline.text,
              backgroundColor: theme.colors.baseline.card,
              padding: `2px 4px`,
              borderRadius: '3px',
              border: `1px solid ${theme.colors.baseline.border}`,
              pointerEvents: 'none',
            }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 0.6;
          }
          50% {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};

export default AgentEdge;
