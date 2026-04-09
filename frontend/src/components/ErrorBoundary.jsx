import { Component } from 'react';
import { AlertTriangle, RefreshCw, Bug } from 'lucide-react';

/**
 * React Error Boundary — wraps a subtree and catches render errors.
 *
 * Props:
 *   componentName  – display name shown in the fallback UI
 *   children       – subtree to protect
 *
 * Usage:
 *   <ErrorBoundary componentName="Dashboard">
 *     <Dashboard ... />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // In production you'd send this to your error tracking service
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  _buildMailto() {
    const { componentName = 'Unknown' } = this.props;
    const { error, errorInfo } = this.state;
    const subject = encodeURIComponent(`Bug in ${componentName} — PredictorPro`);
    const body = encodeURIComponent(
      `Component: ${componentName}\n\n` +
      `Error: ${error?.toString() ?? 'Unknown'}\n\n` +
      `Stack:\n${errorInfo?.componentStack ?? 'N/A'}`
    );
    return `mailto:support@example.com?subject=${subject}&body=${body}`;
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const { componentName = 'Component' } = this.props;
    const isDev = import.meta.env.DEV;

    return (
      <div
        id={`error-boundary-${componentName.toLowerCase().replace(/\s+/g, '-')}`}
        className="flex flex-col items-center justify-center min-h-[200px] p-6 rounded-xl
                   bg-danger/5 border border-danger/30 text-center space-y-4 animate-fade-in"
      >
        {/* Icon */}
        <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-danger" />
        </div>

        {/* Heading */}
        <div>
          <h3 className="font-heading font-bold text-base text-text-primary">
            {componentName} crashed
          </h3>
          <p className="text-sm text-text-muted mt-1">
            Something went wrong rendering this section.
          </p>
        </div>

        {/* Dev mode: show error message */}
        {isDev && this.state.error && (
          <details className="w-full text-left">
            <summary className="text-xs text-danger cursor-pointer font-mono">
              {this.state.error.toString()}
            </summary>
            <pre className="mt-2 text-[10px] text-text-muted overflow-auto max-h-40
                           bg-bg-primary rounded p-2 border border-[#2D3748]">
              {this.state.errorInfo?.componentStack}
            </pre>
          </details>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            id={`retry-btn-${componentName.toLowerCase().replace(/\s+/g, '-')}`}
            onClick={this.handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-accent-green/10 border border-accent-green/30
                       text-accent-green text-sm hover:bg-accent-green/20 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
          <a
            href={this._buildMailto()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-bg-elevated border border-[#2D3748]
                       text-text-muted text-sm hover:text-text-primary transition-all"
          >
            <Bug className="w-3.5 h-3.5" />
            Report Bug
          </a>
        </div>
      </div>
    );
  }
}
