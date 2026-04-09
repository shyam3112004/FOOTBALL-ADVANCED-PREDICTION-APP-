import { Home, LayoutDashboard, Users, Settings, X } from 'lucide-react';
import usePredictionStore from '../store/predictionStore';

const NAV_ITEMS = [
  { id: 'home',      label: 'Home XI',    icon: Home },
  { id: 'dashboard', label: 'Dashboard',  icon: LayoutDashboard },
  { id: 'away',      label: 'Away XI',    icon: Users },
  { id: 'settings',  label: 'Settings',   icon: Settings },
];

/**
 * MobileNav — bottom navigation bar for small screens (< md breakpoint).
 * Controls which panel is visible via Zustand's mobilePanel state.
 */
export default function MobileNav() {
  const { mobilePanel, setMobilePanel } = usePredictionStore();

  return (
    <nav
      id="mobile-bottom-nav"
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden
                 glass border-t border-[#1F2937] safe-area-pb"
      role="navigation"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around px-2 py-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const active = mobilePanel === id;
          return (
            <button
              key={id}
              id={`mobile-nav-${id}`}
              onClick={() => setMobilePanel(id)}
              aria-label={label}
              aria-current={active ? 'page' : undefined}
              className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg
                         transition-all duration-200 min-w-[52px] ${
                active
                  ? 'text-accent-green'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <div
                className={`relative rounded-lg p-1 transition-all duration-200 ${
                  active ? 'bg-accent-green/10' : ''
                }`}
              >
                <Icon
                  className={`w-5 h-5 transition-all duration-200 ${
                    active ? 'text-accent-green' : ''
                  }`}
                />
                {active && (
                  <span
                    className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5
                               rounded-full bg-accent-green animate-pulse"
                  />
                )}
              </div>
              <span
                className={`text-[10px] font-semibold tracking-wide
                            transition-colors duration-200 ${
                  active ? 'text-accent-green' : 'text-text-muted'
                }`}
              >
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/**
 * MatchSetupDrawer — slide-up drawer for selecting league + match on mobile.
 * Triggered by the "Match Setup" button in header on small screens.
 */
export function MatchSetupDrawer({ children, onClose }) {
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden
                   animate-fade-in"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        id="match-setup-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Match Setup"
        className="fixed bottom-0 left-0 right-0 z-50 md:hidden
                   glass border-t border-[#1F2937] rounded-t-2xl
                   animate-slide-up max-h-[85vh] overflow-y-auto"
      >
        {/* Handle */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div className="mx-auto w-10 h-1 rounded-full bg-[#2D3748]" />
          <button
            id="close-match-setup-drawer"
            onClick={onClose}
            className="absolute right-4 top-4 p-1.5 rounded-lg
                       bg-bg-elevated border border-[#2D3748]
                       text-text-muted hover:text-text-primary transition-all"
            aria-label="Close drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content (competition + fixture selectors passed as children) */}
        <div className="px-4 pb-8 space-y-3">
          <h2 className="text-sm font-heading font-bold text-text-primary uppercase
                         tracking-widest text-center">
            Match Setup
          </h2>
          {children}
        </div>
      </div>
    </>
  );
}
