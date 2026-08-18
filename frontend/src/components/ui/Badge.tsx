import React from 'react';
import { cn } from './Card';

// Covers both Decision variants (default/allow/mfa/block) and RiskLevel
// variants (low/medium/high), so RiskBadge.tsx can be a thin wrapper
// around this component instead of duplicating badge styling.
export type BadgeVariant =
  | 'default'
  | 'allow'
  | 'mfa'
  | 'block'
  | 'low'
  | 'medium'
  | 'high';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variants: Record<BadgeVariant, string> = {
      default: 'bg-surfaceHover text-textMuted border-border',

      // Decision variants
      allow: 'bg-decision-allow/10 text-decision-allow border-decision-allow/20',
      mfa: 'bg-decision-mfa/10 text-decision-mfa border-decision-mfa/20',
      block: 'bg-decision-block/10 text-decision-block border-decision-block/20',

      // Risk level variants
      low: 'bg-risk-low/10 text-risk-low border-risk-low/20',
      medium: 'bg-risk-medium/10 text-risk-medium border-risk-medium/20',
      high: 'bg-risk-high/10 text-risk-high border-risk-high/20',
    };

    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";