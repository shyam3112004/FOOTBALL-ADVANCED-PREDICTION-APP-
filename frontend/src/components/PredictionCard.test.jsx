import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';
import { PredictionCard, ProbBar, PredictionCardSkeleton } from './PredictionCard';

describe('ProbBar', () => {
  it('renders probability label as percentage', () => {
    render(<ProbBar label="Home Win (1)" prob={0.55} animate={false} />);
    expect(screen.getByText(/55\.0%/)).toBeInTheDocument();
  });

  it('renders zero probability without errors', () => {
    render(<ProbBar label="Draw" prob={0} animate={false} />);
    expect(screen.getByText(/0\.0%/)).toBeInTheDocument();
  });

  it('renders without label', () => {
    const { container } = render(<ProbBar prob={0.3} animate={false} />);
    expect(container.firstChild).toBeTruthy();
  });
});

describe('PredictionCard', () => {
  it('renders title', () => {
    render(
      <PredictionCard title="1×2 — Match Result">
        <div>content</div>
      </PredictionCard>
    );
    expect(screen.getByText(/1×2/)).toBeInTheDocument();
  });

  it('renders confidence badge when confidence provided', () => {
    render(
      <PredictionCard title="Test" confidence={0.78}>
        <div>content</div>
      </PredictionCard>
    );
    expect(screen.getByText(/78%.*conf/i)).toBeInTheDocument();
  });

  it('does not render confidence badge when confidence is null', () => {
    render(
      <PredictionCard title="Test" confidence={null}>
        <div>content</div>
      </PredictionCard>
    );
    expect(screen.queryByText(/conf\./)).not.toBeInTheDocument();
  });

  it('renders children', () => {
    render(
      <PredictionCard title="Test">
        <span data-testid="child">Hello</span>
      </PredictionCard>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });
});

describe('PredictionCardSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<PredictionCardSkeleton />);
    expect(container.firstChild).toBeTruthy();
  });
});
