/**
 * ErrorBoundary - React error boundary for catching component errors
 */

import React, { ReactNode, ReactElement } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error('Error caught by boundary:', error);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactElement {
    if (this.state.hasError) {
      return (
        <div
          data-testid="error-boundary"
          className="flex items-center justify-center min-h-screen bg-slate-900"
        >
          <div className="rounded-lg bg-slate-800 p-8 text-center max-w-md">
            <h1 className="text-2xl font-bold text-red-500 mb-4">
              Oops, something went wrong
            </h1>
            <p className="text-slate-400 mb-6">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={this.handleRetry}
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-slate-50 hover:bg-blue-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return (
      <div data-testid="error-boundary">
        {this.props.children}
      </div>
    );
  }
}
