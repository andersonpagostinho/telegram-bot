/**
 * ValidationCenter - OpenAI Validator review and approval
 * Shows pending validations, test results, and approval workflow
 */

import React, { useState } from 'react';
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { useValidations } from '../hooks/useValidations';
import { useWebSocket } from '../hooks/useWebSocket';
import { LoadingState, EmptyState, ErrorState } from '../components/common';
import PageHeader from '../components/layout/PageHeader';
import { theme } from '../lib/theme/tokens';

const statusIcons = {
  PENDING: <Clock size={20} color="#FFD700" />,
  APPROVED: <CheckCircle size={20} color="#008000" />,
  REJECTED: <XCircle size={20} color="#FF0000" />,
  IN_REVIEW: <AlertCircle size={20} color="#FF8C00" />,
};

const statusColors = {
  PENDING: '#FFD700',
  APPROVED: '#008000',
  REJECTED: '#FF0000',
  IN_REVIEW: '#FF8C00',
};

export default function ValidationCenter() {
  const { data: validationsData, isLoading, error } = useValidations({ per_page: 100 });
  const { isConnected } = useWebSocket({ eventTypes: ['VALIDATION_REQUESTED', 'VALIDATION_COMPLETED'] });
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error as Error} />;
  if (!validationsData?.validations || validationsData.validations.length === 0) {
    return <EmptyState message="No validations" />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: theme.palette.background.default }}>
      <PageHeader title="Validation Center" subtitle="OpenAI Validator review and approval" />

      <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1000px' }}>
          {validationsData.validations.map((validation) => (
            <div
              key={validation.validation_id}
              style={{
                padding: '16px',
                border: `2px solid ${statusColors[validation.status] || theme.palette.divider}`,
                borderRadius: '8px',
                backgroundColor: theme.palette.background.paper,
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
              onClick={() => setExpandedId(expandedId === validation.validation_id ? null : validation.validation_id)}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 12px rgba(0,0,0,0.15)`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                {statusIcons[validation.status] || <Clock size={20} />}
                <div style={{ flex: 1 }}>
                  <h3 style={{ margin: '0', color: theme.palette.text.primary, fontSize: '16px', fontWeight: 600 }}>
                    Validation for Execution {validation.execution_id?.slice(0, 8)}
                  </h3>
                  <p style={{ margin: '0', color: theme.palette.text.secondary, fontSize: '12px' }}>
                    Mission: {validation.mission_id}
                  </p>
                </div>
                <div
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: statusColors[validation.status] || theme.palette.action.disabledBackground,
                    color: '#fff',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
                >
                  {validation.status}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13px', marginBottom: '12px' }}>
                <div>
                  <span style={{ color: theme.palette.text.secondary }}>Validator: </span>
                  <span style={{ color: theme.palette.text.primary, fontWeight: 500 }}>OpenAI Validator</span>
                </div>
                <div>
                  <span style={{ color: theme.palette.text.secondary }}>Requested: </span>
                  <span style={{ color: theme.palette.text.primary }}>
                    {new Date(validation.created_at || Date.now()).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {expandedId === validation.validation_id && (
                <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: `1px solid ${theme.palette.divider}` }}>
                  <h4 style={{ margin: '0 0 8px 0', color: theme.palette.text.primary, fontSize: '14px', fontWeight: 600 }}>
                    Scope
                  </h4>
                  <p style={{ margin: '0 0 16px 0', color: theme.palette.text.secondary, fontSize: '13px' }}>
                    {validation.scope || 'No scope provided'}
                  </p>

                  {validation.result && (
                    <>
                      <h4 style={{ margin: '0 0 8px 0', color: theme.palette.text.primary, fontSize: '14px', fontWeight: 600 }}>
                        Result
                      </h4>
                      <p style={{ margin: '0 0 16px 0', color: theme.palette.text.secondary, fontSize: '13px' }}>
                        {validation.result}
                      </p>
                    </>
                  )}

                  {validation.tests_executed && validation.tests_executed > 0 && (
                    <div
                      style={{
                        padding: '8px 12px',
                        borderRadius: '4px',
                        backgroundColor: theme.palette.action.disabledBackground,
                        fontSize: '12px',
                        color: theme.palette.text.secondary,
                      }}
                    >
                      ✓ {validation.tests_executed} tests executed
                      {validation.tests_passed && ` - ${validation.tests_passed} passed`}
                      {validation.tests_failed && ` - ${validation.tests_failed} failed`}
                    </div>
                  )}
                </div>
              )}

              <div style={{ marginTop: '12px', fontSize: '11px', color: theme.palette.text.secondary }}>
                {validation.completed_at && (
                  <div>Completed: {new Date(validation.completed_at).toLocaleDateString()}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {!isConnected && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            padding: '12px 16px',
            borderRadius: '4px',
            backgroundColor: '#FFA500',
            color: '#fff',
            fontSize: '12px',
            fontWeight: 500,
          }}
        >
          ⚠️ WebSocket disconnected
        </div>
      )}
    </div>
  );
}
