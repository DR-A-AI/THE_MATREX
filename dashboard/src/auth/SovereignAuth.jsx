import React, { createContext, useContext, useState, useEffect, Component } from 'react';
import { 
  ClerkProvider as BaseClerkProvider, 
  useUser as baseUseUser, 
  useAuth as baseUseAuth,
  UserButton as BaseUserButton
} from '@clerk/clerk-react';
import { Shield, Terminal, CheckCircle2, AlertTriangle } from 'lucide-react';

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const isClerkConfigured = Boolean(clerkPubKey && clerkPubKey.trim() !== '');

// Official registered Commander identity from Clerk instance
export const DEFAULT_COMMANDER = {
  id: 'user_3EyRW18sYfOG6QVvwu7wF1BDhYz',
  primaryEmailAddress: { emailAddress: 'r11salfd@gmail.com' },
  fullName: '11salfd (Sovereign Commander)',
  firstName: '11salfd',
  imageUrl: null,
};

const AuthContext = createContext({
  isSignedIn: true,
  isLoaded: true,
  user: DEFAULT_COMMANDER,
  isClerkLive: false,
  getToken: async () => 'sovereign_commander_token_123',
});

// Resilient Error Boundary to catch any Clerk SDK network/script errors
class ClerkErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.warn('[SovereignAuth] Clerk Cloud unreachable or blocked by network/ad-blocker. Falling back to Sovereign Commander Mode:', error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

// Inner watcher inside BaseClerkProvider that safely syncs Clerk cloud session
function ClerkStateWatcher({ children, onSync }) {
  try {
    const auth = baseUseAuth();
    const user = baseUseUser();

    useEffect(() => {
      if (auth?.isSignedIn && user?.user) {
        onSync({
          isSignedIn: true,
          isLoaded: true,
          user: user.user,
          isClerkLive: true,
          getToken: auth.getToken || (async () => 'sovereign_commander_token_123'),
        });
      }
    }, [auth?.isSignedIn, user?.user, onSync]);
  } catch (err) {
    console.warn('[SovereignAuth] Clerk hook evaluation failed:', err);
  }

  return <>{children}</>;
}

export function SovereignAuthProvider({ children }) {
  const [authState, setAuthState] = useState({
    isSignedIn: true, // Always auto-authenticated for Commander
    isLoaded: true,
    user: DEFAULT_COMMANDER,
    isClerkLive: false,
    getToken: async () => 'sovereign_commander_token_123',
  });

  const localProvider = (
    <AuthContext.Provider value={authState}>
      {children}
    </AuthContext.Provider>
  );

  // If Clerk is not configured, run purely local
  if (!isClerkConfigured) {
    return localProvider;
  }

  // If configured, attempt to wrap with ClerkProvider protected by ErrorBoundary
  return (
    <ClerkErrorBoundary fallback={localProvider}>
      <BaseClerkProvider 
        publishableKey={clerkPubKey}
        standardBrowser={true}
      >
        <ClerkStateWatcher onSync={setAuthState}>
          <AuthContext.Provider value={authState}>
            {children}
          </AuthContext.Provider>
        </ClerkStateWatcher>
      </BaseClerkProvider>
    </ClerkErrorBoundary>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useUser() {
  const ctx = useContext(AuthContext);
  return {
    isSignedIn: ctx.isSignedIn,
    isLoaded: ctx.isLoaded,
    user: ctx.user,
  };
}

/**
 * SignedIn: In Auto-Auth mode, always renders children.
 * The application is never blocked behind a blank or locked screen.
 */
export function SignedIn({ children }) {
  return <>{children}</>;
}

/**
 * SignedOut: User is never blocked as signed out.
 */
export function SignedOut({ children }) {
  return null;
}

export function UserButton() {
  const { user, isClerkLive } = useContext(AuthContext);

  if (isClerkLive && user?.id !== DEFAULT_COMMANDER.id) {
    try {
      return <BaseUserButton />;
    } catch {
      // Fallback if BaseUserButton fails
    }
  }

  return (
    <div 
      className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[rgba(0,243,255,0.15)] border border-[#00f3ff] text-[#00f3ff] text-xs font-mono shadow-[0_0_10px_rgba(0,243,255,0.3)]"
      title={`Auto-Authenticated as ${user?.primaryEmailAddress?.emailAddress || 'Commander'}`}
    >
      <Terminal size={14} className="animate-pulse" />
      <span className="font-bold tracking-wider">{user?.firstName || 'COMMANDER'}</span>
      <span className="w-2 h-2 rounded-full bg-[#00ff88] shadow-[0_0_6px_#00ff88]" />
    </div>
  );
}

export function SignIn() {
  useEffect(() => {
    // If ever navigated to SignIn, auto-route to dashboard root
    window.location.hash = '#/';
  }, []);

  return (
    <div className="flex flex-col items-center gap-4 text-center p-6 border border-[#00f3ff]/30 rounded-xl bg-black/60 font-mono">
      <CheckCircle2 size={48} className="text-[#00ff88] animate-bounce" />
      <h2 className="text-xl font-bold text-[#00f3ff]">AUTO-AUTHENTICATION ACTIVE</h2>
      <p className="text-xs text-gray-300">
        Authenticated as Sovereign Commander <span className="text-[#00f3ff] font-bold">11salfd (r11salfd@gmail.com)</span>.
      </p>
      <p className="text-xs text-[#00f3ff]/60">Entering Command Deck...</p>
    </div>
  );
}
