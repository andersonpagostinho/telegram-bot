/**
 * PageHeader - Page title and optional action area
 */

import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function PageHeader({
  title,
  description,
  action,
}: PageHeaderProps) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div className="flex-1">
        <h1 className="text-2xl font-bold text-slate-50">{title}</h1>
        {description && (
          <p className="mt-1 text-slate-400">{description}</p>
        )}
      </div>
      {action && (
        <div className="flex items-center">
          {action}
        </div>
      )}
    </div>
  );
}
