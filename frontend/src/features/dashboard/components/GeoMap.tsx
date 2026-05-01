import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  useTheme,
  Tooltip,
  styled,
  IconButton
} from '@mui/material';
import { Globe, MapPin, Plus } from 'lucide-react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup
} from 'react-simple-maps';
import { scaleLinear } from 'd3-scale';

// Tactical Glowing Marker
const PulsingDot = styled('div')(({ color }: { color: string }) => ({
  width: 8,
  height: 8,
  backgroundColor: color,
  borderRadius: '50%',
  boxShadow: `0 0 10px ${color}`,
  position: 'relative',
  '&::after': {
    content: '""',
    position: 'absolute',
    top: -4,
    left: -4,
    right: -4,
    bottom: -4,
    borderRadius: '50%',
    border: `2px solid ${color}`,
    animation: 'pulse 2s infinite',
    opacity: 0
  },
  '@keyframes pulse': {
    '0%': { transform: 'scale(0.5)', opacity: 0.8 },
    '100%': { transform: 'scale(2.5)', opacity: 0 }
  }
}));

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Basic Centroid Mapping for Tactical Markers
const countryCentroids: Record<string, [number, number]> = {
  'US': [-95.7129, 37.0902], 'IN': [78.9629, 20.5937], 'GB': [-3.4360, 55.3781], 'CN': [104.1954, 35.8617],
  'DE': [10.4515, 51.1657], 'BR': [-51.9253, -14.2350], 'RU': [105.3188, 61.5240], 'AU': [133.7751, -25.2744],
  'FR': [2.2137, 46.2276], 'CA': [-106.3468, 56.1304], 'JP': [138.2529, 36.2048], 'SG': [103.8198, 1.3521],
  'NL': [5.2913, 52.1326], 'IE': [-8.2439, 53.4129], 'PK': [69.3451, 30.3753], 'ID': [113.9213, -0.7893],
  'VN': [108.2772, 14.0583], 'TH': [100.9925, 15.8700], 'AE': [53.8478, 23.4241], 'SA': [45.0792, 23.8859],
};

interface CountryData {
  name: string;
  iso: string;
  count: number;
}

export const GeoMap: React.FC<{ data: CountryData[] }> = ({ data }) => {
  const theme = useTheme();

  const colorScale = scaleLinear<string>()
    .domain([0, Math.max(...data.map(d => d.count), 1)])
    .range(["rgba(0, 243, 255, 0.05)", "rgba(0, 243, 255, 0.4)"]);

  const findCountry = (geo: any) => {
    const geoName = (geo.properties.name || "").toUpperCase();
    return data.find(d =>
      d.iso.toUpperCase() === geoName ||
      d.name.toUpperCase() === geoName ||
      (d.name.toUpperCase() === "UNITED STATES" && geoName === "UNITED STATES OF AMERICA") ||
      (d.iso.toUpperCase() === "GB" && geoName === "UNITED KINGDOM")
    );
  };

  return (
    <Card sx={{
      height: 500,
      bgcolor: 'rgba(5, 5, 15, 0.6)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(0, 243, 255, 0.1)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <CardContent sx={{ p: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5, borderBottom: '1px solid rgba(0, 243, 255, 0.1)' }}>
          <Globe size={20} color="#00f3ff" style={{ filter: 'drop-shadow(0 0 5px #00f3ff)' }} />
          <Typography variant="h6" sx={{
            fontSize: '0.85rem',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: 2,
            fontFamily: 'Orbitron',
            color: '#fff'
          }}>
            Geographical Distribution of Assets
          </Typography>
        </Box>

        <Grid container sx={{ flexGrow: 1, minHeight: 0 }}>
          {/* Map Column */}
          <Grid size={{ xs: 12, md: 8 }} sx={{ position: 'relative', bgcolor: 'rgba(0,0,0,0.3)', height: '100%' }}>
            {/* Zoom Controls Overlay */}
            <Box sx={{ position: 'absolute', top: 10, left: 10, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <IconButton
                size="small"
                sx={{ bgcolor: 'rgba(5, 5, 20, 0.8)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1, p: 0.5, '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
              >
                <Plus size={14} />
              </IconButton>
              <IconButton
                size="small"
                sx={{ bgcolor: 'rgba(5, 5, 20, 0.8)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1, p: 0.5, '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
              >
                <Box sx={{ width: 14, height: 2, bgcolor: 'currentColor' }} />
              </IconButton>
            </Box>

            <ComposableMap projectionConfig={{ scale: 200, center: [15, 5] }} style={{ width: "100%", height: "100%" }}>
              <defs>
                <pattern id="dotPattern" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                  <circle cx="1" cy="1" r="0.8" fill="rgba(0, 243, 255, 0.2)" />
                </pattern>
                <pattern id="dotPatternActive" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
                  <circle cx="1" cy="1" r="1" fill="rgba(0, 243, 255, 0.8)" />
                </pattern>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <ZoomableGroup zoom={1} maxZoom={3}>
                <Geographies geography={geoUrl}>
                  {({ geographies }) =>
                    geographies.map((geo) => {
                      const country = findCountry(geo);
                      return (
                        <g key={geo.rsmKey}>
                          {/* Base Layer for Background Color/Glow */}
                          <Geography
                            geography={geo}
                            fill={country ? "rgba(0, 243, 255, 0.15)" : "rgba(255, 255, 255, 0.02)"}
                            stroke="rgba(0, 243, 255, 0.1)"
                            strokeWidth={0.3}
                            style={{
                              default: { outline: "none" },
                              hover: { fill: "rgba(0, 243, 255, 0.3)", cursor: 'pointer' },
                              pressed: { outline: "none" }
                            }}
                          />
                          {/* Pattern Layer */}
                          <Geography
                            geography={geo}
                            fill={country ? "url(#dotPatternActive)" : "url(#dotPattern)"}
                            stroke="none"
                            pointerEvents="none"
                            style={{
                              default: {
                                outline: "none",
                                filter: country ? "url(#glow)" : "none"
                              }
                            }}
                          />
                        </g>
                      );
                    })
                  }
                </Geographies>

                {/* Markers for Countries with Assets */}
                {data.map((country) => {
                  const coords = countryCentroids[country.iso.toUpperCase()];
                  if (!coords) return null;
                  return (
                    <Marker key={country.iso} coordinates={coords}>
                      <Tooltip title={`${country.name}: ${country.count} Assets`} arrow>
                        <g>
                          <circle r={4} fill="rgba(0, 243, 255, 0.2)" />
                          <foreignObject x="-10" y="-10" width="20" height="20">
                            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', height: '100%' }}>
                              <PulsingDot color="#00f3ff" />
                            </div>
                          </foreignObject>
                        </g>
                      </Tooltip>
                    </Marker>
                  );
                })}
              </ZoomableGroup>
            </ComposableMap>
          </Grid>

          {/* List Column */}
          <Grid size={{ xs: 12, md: 4 }} sx={{ borderLeft: '1px solid rgba(0, 243, 255, 0.1)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <TableContainer sx={{ flexGrow: 1, overflow: 'auto', '&::-webkit-scrollbar': { width: 4 }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: 2 } }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ bgcolor: 'rgba(5,5,15,0.98)', borderBottom: '2px solid #7000ff', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800, fontFamily: 'Orbitron', py: 1.5 }}>COUNTRY</TableCell>
                    <TableCell align="right" sx={{ bgcolor: 'rgba(5,5,15,0.98)', borderBottom: '2px solid #7000ff', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800, fontFamily: 'Orbitron', py: 1.5 }}>ASSETS</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={2} align="center" sx={{ py: 4, border: 'none', opacity: 0.5 }}>
                        <Typography variant="caption" sx={{ letterSpacing: 1 }}>NO_NODES_DETECTED</Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.sort((a, b) => b.count - a.count).map((country) => (
                      <TableRow key={country.iso} sx={{ '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.05)' } }}>
                        <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.03)', py: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                            <Box
                              component="span"
                              className={`fi fi-${country.iso.toLowerCase()}`}
                              sx={{
                                width: 20,
                                height: 14,
                                borderRadius: '2px',
                                border: '1px solid rgba(255,255,255,0.1)',
                                boxShadow: '0 0 5px rgba(0,0,0,0.5)'
                              }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', color: 'rgba(255,255,255,0.9)' }}>
                              {country.name}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="right" sx={{ borderBottom: '1px solid rgba(255,255,255,0.03)', py: 2 }}>
                          <Typography variant="body2" sx={{ fontWeight: 900, fontSize: '0.85rem', color: '#b6b9baff', fontFamily: 'Orbitron' }}>
                            {country.count}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};
