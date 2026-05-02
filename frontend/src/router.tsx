import { createRootRoute, createRoute, createRouter, Outlet, Link } from "@tanstack/react-router";
import { Shell } from "./components/Shell";
import { DashboardPage } from "./features/dashboard";
import { TargetList, TargetSummary } from "./features/targets";
import { MonitoringPage } from "./features/monitoring";
import { EnginesPage } from "./features/engines";
import { ProjectsPage } from "./features/projects";
import { ScanList, ScheduledScansPage, SubScansPage, ScanHistoryPage, ScanDetailPage } from "./features/scans";
import { EndpointsPage } from "./features/endpoints";
import { SubdomainsPage } from "./features/subdomains";

import { PlaceholderPage } from "./components/PlaceholderPage";
import { Box, Typography, Button } from "@mui/material";
import { AlertCircle, Home, RefreshCw, Activity, ShieldAlert, Clock, Globe, Target } from "lucide-react";

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

const projectsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "projects",
  component: ProjectsPage,
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
  component: ScanHistoryPage,
  loader: async ({ params: { projectSlug } }) => {
    return { projectSlug };
  },
});

// Sub Scans Route
const subScansRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "scans/sub",
  component: SubScansPage,
  loader: async ({ params: { projectSlug } }) => {
    return { projectSlug };
  },
  pendingComponent: () => (
    <Box sx={{ 
      height: '80vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      gap: 3
    }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.2s' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.4s' }} />
      </Box>
      <Typography sx={{ 
        fontFamily: 'Orbitron', 
        fontWeight: 900, 
        letterSpacing: 2, 
        fontSize: '14px',
        color: '#00f3ff',
        textAlign: 'center'
      }}>
        ACCESSING TACTICAL REGISTRY... <br/>
        <span style={{ fontSize: '10px', opacity: 0.5, color: '#fff' }}>RETRIEVING SUB SCANS... PLEASE WAIT</span>
      </Typography>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.5); opacity: 1; }
          }
        `}
      </style>
    </Box>
  )
});

// Scheduled Scans Route
const scheduledScansRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "scans/scheduled",
  component: ScheduledScansPage,
  loader: async ({ params: { projectSlug } }) => {
    return { projectSlug };
  },
  pendingComponent: () => (
    <Box sx={{ 
      height: '80vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      gap: 3
    }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.2s' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.4s' }} />
      </Box>
      <Typography sx={{ 
        fontFamily: 'Orbitron', 
        fontWeight: 900, 
        letterSpacing: 2, 
        fontSize: '14px',
        color: '#00f3ff',
        textAlign: 'center'
      }}>
        ACCESSING TACTICAL REGISTRY... <br/>
        <span style={{ fontSize: '10px', opacity: 0.5, color: '#fff' }}>RETRIEVING SCHEDULED OPERATIONS... PLEASE WAIT</span>
      </Typography>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.5); opacity: 1; }
          }
        `}
      </style>
    </Box>
  )
});

// All Subdomains Route
const subdomainsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "subdomains",
  component: SubdomainsPage,
  loader: async ({ params: { projectSlug } }) => {
    // This triggers the pendingComponent while the initial fetch is happening
    // We don't necessarily need to return the data here since useQuery handles it,
    // but having a promise here ensures the "pending" state is active.
    return { projectSlug };
  },
  pendingComponent: () => (
    <Box sx={{ 
      height: '80vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      gap: 3
    }}>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.2s' }} />
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#00f3ff', animation: 'pulse 1.5s infinite ease-in-out 0.4s' }} />
      </Box>
      <Typography sx={{ 
        fontFamily: 'Orbitron', 
        fontWeight: 900, 
        letterSpacing: 2, 
        fontSize: '14px',
        color: '#00f3ff',
        textAlign: 'center'
      }}>
        INITIALIZING TACTICAL DATA... <br/>
        <span style={{ fontSize: '10px', opacity: 0.5, color: '#fff' }}>FETCHING SUBDOMAINS... PLEASE WAIT</span>
      </Typography>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.5); opacity: 1; }
          }
        `}
      </style>
    </Box>
  )
});

// All Endpoints Route
const endpointsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "endpoints",
  component: EndpointsPage,
});

// Vulnerabilities Route
const vulnsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "vulns",
  component: () => <PlaceholderPage title="Vulnerabilities" icon={<ShieldAlert size={48} />} />,
});

// Scan History Detail Route
const scanDetailRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "scan/detail/$scanId",
  component: ScanDetailPage,
});

// Route Tree
const routeTree = rootRoute.addChildren([
  rootRedirectRoute,
  projectRoute.addChildren([
    projectsRoute,
    dashboardRoute,

    targetListRoute,
    targetSummaryRoute,
    monitoringRoute,
    enginesRoute,
    scansRoute,
    subScansRoute,
    scanDetailRoute,
    scheduledScansRoute,
    subdomainsRoute,
    endpointsRoute,
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
