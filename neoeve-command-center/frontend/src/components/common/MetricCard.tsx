/**
 * MetricCard - Display a metric with value, label, and optional variation
 */

import React from 'react';

interface Variation {
  value: number;
  type: 'increase' | 'decrease' | 'neutral';
}

interface MetricCardProps {
  label: string;
  value: number | null;
  description?: string;
  variation?: Variation;
}

export default function MetricCard({
  label,
  value,
  description,
  variation,
}: MetricCardProps) {
  const getVariationColor = () => {
    switch (variation?.type) {
      case 'increase':
        return 'text-green-500';
      case 'decrease':
        return 'text-red-500';
      default:
        return 'text-slate-400';
    }
  };

  const getVariationSymbol = () => {
    switch (variation?.type) {
      case 'increase':
        return '↑';
      case 'decrease':
        return '↓';
      default:
        return '→';
    }
  };

  return (
    <div className="rounded-lg bg-slate-800 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-50">
            {value !== null && value !== undefined ? value : '—'}
          </p>
        </div>
        {variation && value !== null && (
          <div
            data-testid="metric-variation"
            className={`text-lg font-semibold ${getVariationColor()}`}
          >
            {getVariationSymbol()} {Math.abs(variation.value)}
          </div>
        )}
      </div>
      {description && (
        <p
          data-testid="metric-description"
          className="mt-2 text-xs text-slate-400"
        >
          {description}
        </p>
      )}
    </div>
  );
}
