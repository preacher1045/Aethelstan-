'use client';

import React, { Component, ReactNode } from 'react';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    errorInfo: React.ErrorInfo | null;
}

/**
 * Error Boundary component to catch React rendering errors
 * and display a fallback UI instead of crashing the entire app.
 * 
 * Usage:
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = {
        hasError: false,
        error: null,
        errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
        // Update state so the next render will show the fallback UI
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error details for debugging
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
        error,
        errorInfo,
        });
    }

    handleReset = () => {
        this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        });
    };

    render() {
        if (this.state.hasError) {
        // Custom fallback UI
        if (this.props.fallback) {
            return this.props.fallback;
        }

        // Default fallback UI
        return (
            <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 px-4">
            <div className="max-w-2xl w-full">
                <div className="bg-white dark:bg-zinc-900 border border-red-200 dark:border-red-800 rounded-lg shadow-lg p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-12 h-12 bg-red-100 dark:bg-red-950/20 rounded-full flex items-center justify-center">
                    <svg
                        className="w-6 h-6 text-red-600 dark:text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                    </svg>
                    </div>
                    <div>
                    <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                        Something went wrong
                    </h1>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                        An unexpected error occurred while rendering this component
                    </p>
                    </div>
                </div>

                <div className="bg-red-50 dark:bg-red-950/10 border border-red-200 dark:border-red-900/50 rounded-lg p-4 mb-6">
                    <p className="text-sm font-semibold text-red-800 dark:text-red-300 mb-2">
                    Error Details:
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-400 font-mono wrap-break-word">
                    {this.state.error?.message || 'Unknown error'}
                    </p>
                </div>

                {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
                    <details className="mb-6">
                    <summary className="cursor-pointer text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100">
                        Component Stack Trace
                    </summary>
                    <pre className="mt-3 text-xs text-zinc-600 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 p-4 rounded overflow-x-auto">
                        {this.state.errorInfo.componentStack}
                    </pre>
                    </details>
                )}

                <div className="flex gap-3">
                    <button
                    onClick={this.handleReset}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                    >
                    Try Again
                    </button>
                    <button
                    onClick={() => window.location.href = '/'}
                    className="px-4 py-2 bg-zinc-200 hover:bg-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-zinc-100 font-medium rounded-lg transition-colors"
                    >
                    Go to Home
                    </button>
                </div>
                </div>
            </div>
            </div>
        );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
