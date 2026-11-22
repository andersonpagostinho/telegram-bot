/**
 * StatusIndicator - Display operational and connectivity status
 * Separates connectivity (ONLINE/OFFLINE) from operational state (IDLE/WORKING/REVIEWING/etc)
 */

import React from 'react';
import clsx from 'clsx';

interface StatusIndicatorProps {
  status: string;
  connectivity: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function StatusIndicator({
  status,
  connectivity,
  size = 'md',
}: StatusIndicatorProps) {
  const isOnline = connectivity === 'ONLINE';
  const isWorking = status === 'WORKING';

  const getStatusColor = () => {
    if (!isOnline) return 'text-red-500 bg-red-500/10';
    if (isWorking) return 'text-yellow-500 bg-yellow-500/10';
    return 'text-green-500 bg-green-500/10';
  };

  const getDotColor = () => {
    if (!isOnline) return 'bg-red-500';
    if (isWorking) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-1.5 w-1.5';
      case 'lg':
        return 'h-3 w-3';
      default:
        return 'h-2 w-2';
    }
  };

  const getTextSize = () => {
    switch (size) {
      case 'sm':
        return 'text-xs';
      case 'lg':
        return 'text-base';
      default:
        return 'text-sm';
    }
  };

  const displayText = !isOnline ? 'OFFLINE' : status;

  return (
    <div
      data-testid="status-indicator"
      className={clsx('inline-flex items-center gap-2 rounded-full px-3 py-1', getStatusColor())}
    >
      <span className={clsx('rounded-full', getSizeClasses(), getDotColor())} />
      <span className={clsx('font-medium', getTextSize())}>{displayText}</span>
    </div>
  );
}
