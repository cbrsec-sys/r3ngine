import { createRootRoute, createRoute, createRouter, Outlet, Link } from "@tanstack/react-router";
import { Shell } from "./components/Shell";
import { DashboardPage } from "./features/dashboard";
import { TargetList, TargetSummary } from "./features/targets";
import { MonitoringPage } from "./features/monitoring";
import { EnginesPage } from "./features/engines";
import { ScanList } from "./features/scans/components/ScanList";
import { PlaceholderPage } from "./components/PlaceholderPage";
import { Box, Typography, Button } from "@mui/material";
import { AlertCircle, Home, RefreshCw, Activity, ShieldAlert } from "lucide-react";

// Root Route
const rootRoute = createRootRoute({
  component: () => (
    <Shell>
      <Outlet />
    </Shell>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: (props) => <ErrorComponent {...props} />,
});

// Project-specific layout route
const projectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "$projectSlug",
});

// Dashboard Route
const dashboardRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "dashboard",
  component: DashboardPage,
});

// Root to Dashboard redirect
const rootRedirectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
});

// Targets Route
const targetListRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "targets",
  component: TargetList,
});

// Target Summary Route
const targetSummaryRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "target/$targetId/summary",
  component: TargetSummary,
});

// Monitoring Route
const monitoringRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "monitoring",
  component: MonitoringPage,
});

// Engines Route
const enginesRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "engines",
  component: EnginesPage,
});

// Scans Route
const scansRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "scans",
  component: ScanList,
});

// Vulnerabilities Route
const vulnsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "vulns",
  component: () => <PlaceholderPage title="Vulnerabilities" icon={<ShieldAlert size={48} />} />,
});

// Route Tree
const routeTree = rootRoute.addChildren([
  rootRedirectRoute,
  projectRoute.addChildren([
    dashboardRoute,
    targetListRoute,
    targetSummaryRoute,
    monitoringRoute,
    enginesRoute,
    scansRoute,
    vulnsRoute,
  ]),
]);

// Router Instance
export const router = createRouter({ 
  routeTree,
  defaultNotFoundComponent: () => <NotFound />,
});

// Type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

// Components
function NotFound() {
  return (
    <Box
      sx={{
        height: '80vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        background: 'radial-gradient(circle at center, rgba(255, 0, 60, 0.05) 0%, transparent 70%)',
      }}
    >
      <Box sx={{ position: 'relative', mb: 4 }}>
        <AlertCircle size={120} color="#ff003c" style={{ opacity: 0.8 }} />
        <Box sx={{ 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          boxShadow: '0 0 50px rgba(255, 0, 60, 0.3)',
          borderRadius: '50%'
        }} />
      </Box>
      
      <Typography variant="h1" sx={{ 
        fontFamily: 'Orbitron', 
        fontWeight: 900, 
        fontSize: { xs: '3rem', md: '5rem' },
        letterSpacing: 8,
        mb: 2,
        color: '#fff',
        textShadow: '0 0 20px rgba(255, 0, 60, 0.5)'
      }}>
        SIGNAL_LOST
      </Typography>
      
      <Typography variant="h5" sx={{ 
        fontFamily: 'Orbitron',
        color: '#ff003c',
        mb: 4,
        letterSpacing: 2,
        fontWeight: 700
      }}>
        UNAUTHORIZED_SECTOR_ACCESS
      </Typography>
      
      <Typography variant="body1" sx={{ color: 'rgba(255, 255, 255, 0.6)', maxWidth: 500, mb: 6, lineHeight: 1.8 }}>
        The tactical coordinates you provided do not match any known sectors in the reNgine perimeter. 
        Return to base or verify the target parameters.
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 3 }}>
        <Button 
          component={Link}
          to="/"
          variant="outlined" 
          startIcon={<Home size={18} />}
          sx={{ 
            borderColor: 'rgba(255, 255, 255, 0.2)',
            color: '#fff',
            px: 4,
            py: 1.5,
            '&:hover': { borderColor: 'primary.main', bgcolor: 'rgba(0, 243, 255, 0.05)' }
          }}
        >
          RETURN TO DASHBOARD
        </Button>
        <Button 
          onClick={() => window.location.reload()}
          variant="outlined" 
          startIcon={<RefreshCw size={18} />}
          sx={{ 
            borderColor: '#ff003c',
            color: '#ff003c',
            px: 4,
            py: 1.5,
            '&:hover': { bgcolor: 'rgba(255, 0, 60, 0.1)', borderColor: '#ff003c' }
          }}
        >
          RECONNECT SIGNAL
        </Button>
      </Box>
    </Box>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <Box
      sx={{
        height: '80vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        p: 3
      }}
    >
      <AlertCircle size={80} color="#ff003c" style={{ marginBottom: 20 }} />
      <Typography variant="h3" sx={{ fontFamily: 'Orbitron', mb: 2, color: '#fff' }}>SYSTEM_CRASH</Typography>
      <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.7)', mb: 4, maxWidth: 600 }}>
        An unexpected error occurred in the tactical interface. 
        Error: {error.message}
      </Typography>
      <Button 
        variant="contained" 
        onClick={reset}
        sx={{ bgcolor: '#ff003c', '&:hover': { bgcolor: '#cc0030' } }}
      >
        REBOOT INTERFACE
      </Button>
    </Box>
  );
}
