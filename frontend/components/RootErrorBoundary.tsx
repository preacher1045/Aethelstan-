'use client';

import { ReactNode } from 'react';
import ErrorBoundary from '@/components/ErrorBoundary';

interface RootErrorBoundaryProps {
  children: ReactNode;
}

/**
 * Client-side wrapper for the root ErrorBoundary.
 * Used in the root layout to catch rendering errors across the app.
 */
export default function RootErrorBoundary({ children }: RootErrorBoundaryProps) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
