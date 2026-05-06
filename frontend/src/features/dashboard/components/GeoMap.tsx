import React, { useRef } from 'react';
import {
    Box,
    Card,
    CardContent,
    Typography,
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
import { Globe, Plus } from 'lucide-react';
import { MapContainer, TileLayer, GeoJSON, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
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

// Basic Centroid Mapping for Tactical Markers
const countryCentroids: Record<string, [number, number]> = {
    'US': [37.0902, -95.7129], 'IN': [20.5937, 78.9629], 'GB': [55.3781, -3.4360], 'CN': [35.8617, 104.1954],
    'DE': [51.1657, 10.4515], 'BR': [-14.2350, -51.9253], 'RU': [61.5240, 105.3188], 'AU': [-25.2744, 133.7751],
    'FR': [46.2276, 2.2137], 'CA': [56.1304, -106.3468], 'JP': [36.2048, 138.2529], 'SG': [1.3521, 103.8198],
    'NL': [52.1326, 5.2913], 'IE': [53.4129, -8.2439], 'PK': [30.3753, 69.3451], 'ID': [-0.7893, 113.9213],
    'VN': [14.0583, 108.2772], 'TH': [15.8700, 100.9925], 'AE': [23.4241, 53.8478], 'SA': [23.8859, 45.0792],
};

interface CountryData {
    name: string;
    iso: string;
    count: number;
}

interface GeoJSONFeature {
    type: 'Feature';
    properties: Record<string, any>;
    geometry: any;
}

interface GeoJSONFeatureCollection {
    type: 'FeatureCollection';
    features: GeoJSONFeature[];
}

export const GeoMap: React.FC<{ data: CountryData[]; disableCard?: boolean }> = ({ data, disableCard = false }) => {
    const theme = useTheme();
    const mapRef = useRef<L.Map>(null);
    const geoJsonRef = useRef<GeoJSONFeatureCollection | null>(null);

    const colorScale = scaleLinear<string>()
        .domain([0, Math.max(...data.map(d => d.count), 1)])
        .range(["rgba(0, 243, 255, 0.05)", "rgba(0, 243, 255, 0.4)"]);

    const findCountry = (properties: any) => {
        const geoName = (properties.name || "").toUpperCase();
        return data.find(d =>
            d.iso.toUpperCase() === geoName ||
            d.name.toUpperCase() === geoName ||
            (d.name.toUpperCase() === "UNITED STATES" && geoName === "UNITED STATES OF AMERICA") ||
            (d.iso.toUpperCase() === "GB" && geoName === "UNITED KINGDOM")
        );
    };

    const onEachFeature = (feature: GeoJSONFeature, layer: L.Layer) => {
        const country = findCountry(feature.properties);
        const pathLayer = layer as L.Path;

        if (country) {
            const fillColor = colorScale(country.count);
            pathLayer.setStyle({
                fillColor: fillColor,
                fillOpacity: 0.8,
                color: 'rgba(0, 243, 255, 0.1)',
                weight: 0.3
            });
        } else {
            pathLayer.setStyle({
                fillColor: 'rgba(255, 255, 255, 0.02)',
                fillOpacity: 0.8,
                color: 'rgba(0, 243, 255, 0.1)',
                weight: 0.3
            });
        }

        pathLayer.on('mouseover', function (this: L.Path) {
            this.setStyle({
                fillColor: 'rgba(0, 243, 255, 0.3)'
            });
            (this.getElement() as HTMLElement).style.cursor = 'pointer';
        });

        pathLayer.on('mouseout', function (this: L.Path) {
            const countryData = findCountry(feature.properties);
            if (countryData) {
                this.setStyle({
                    fillColor: colorScale(countryData.count)
                });
            } else {
                this.setStyle({
                    fillColor: 'rgba(255, 255, 255, 0.02)'
                });
            }
        });
    };

    const handleZoomIn = () => {
        if (mapRef.current) {
            mapRef.current.zoomIn();
        }
    };

    const handleZoomOut = () => {
        if (mapRef.current) {
            mapRef.current.zoomOut();
        }
    };

    // Fetch and parse GeoJSON data
    const [geoJsonData, setGeoJsonData] = React.useState<GeoJSONFeatureCollection | null>(null);

    React.useEffect(() => {
        const fetchGeoJson = async () => {
            try {
                const response = await fetch(
                    'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson'
                );
                const json: GeoJSONFeatureCollection = await response.json();
                setGeoJsonData(json);
            } catch (error) {
                console.error('Error fetching GeoJSON:', error);
            }
        };

        fetchGeoJson();
    }, []);

    const content = (
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, minHeight: 0, width: '100%', height: 500 }}>
            {/* Map Column */}
            <Box sx={{ flex: '1 1 65%', position: 'relative', bgcolor: 'rgba(0,0,0,0.3)', height: '100%' }}>
                {/* Zoom Controls Overlay */}
                <Box sx={{ position: 'absolute', top: 10, left: 10, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    <IconButton
                        size="small"
                        onClick={handleZoomIn}
                        sx={{ bgcolor: 'rgba(5, 5, 20, 0.8)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1, p: 0.5, '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
                    >
                        <Plus size={14} />
                    </IconButton>
                    <IconButton
                        size="small"
                        onClick={handleZoomOut}
                        sx={{ bgcolor: 'rgba(5, 5, 20, 0.8)', color: '#00f3ff', border: '1px solid rgba(0, 243, 255, 0.2)', borderRadius: 1, p: 0.5, '&:hover': { bgcolor: 'rgba(0, 243, 255, 0.1)' } }}
                    >
                        <Box sx={{ width: 14, height: 2, bgcolor: 'currentColor' }} />
                    </IconButton>
                </Box>

                <MapContainer
                    ref={mapRef}
                    center={[5, 15]}
                    zoom={2}
                    minZoom={1}
                    maxZoom={3}
                    style={{ width: '100%', height: '100%' }}
                    zoomControl={false}
                    attributionControl={false}
                    dragging={true}
                    touchZoom={true}
                >
                    <TileLayer
                        url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
                        attribution=""
                    />
                    {geoJsonData && (
                        <GeoJSON data={geoJsonData} onEachFeature={onEachFeature} />
                    )}

                    {/* Markers for Countries with Assets */}
                    {data.map((country) => {
                        const coords = countryCentroids[country.iso.toUpperCase()];
                        if (!coords) return null;

                        return (
                            <Marker
                                key={country.iso}
                                position={coords}
                                icon={L.divIcon({
                                    html: `<div style="display: flex; justify-content: center; align-items: center; width: 100%; height: 100%;"><div style="width: 8px; height: 8px; background-color: #00f3ff; border-radius: 50%; box-shadow: 0 0 10px #00f3ff; position: relative;"><style>@keyframes pulse { 0% { box-shadow: 0 0 10px #00f3ff, 0 0 0px 2px #00f3ff; } 100% { box-shadow: 0 0 10px #00f3ff, 0 0 15px 8px rgba(0,243,255,0); } } div { animation: pulse 2s infinite; }</style></div></div>`,
                                    iconSize: [20, 20],
                                    iconAnchor: [10, 10],
                                    popupAnchor: [0, -10],
                                    className: 'custom-marker'
                                })}
                            >
                                <Tooltip title={`${country.name}: ${country.count} Assets`} arrow>
                                    <span />
                                </Tooltip>
                            </Marker>
                        );
                    })}
                </MapContainer>
            </Box>

            {/* List Column */}
            <Box sx={{ width: { xs: '100%', md: '35%' }, borderLeft: { xs: 'none', md: '1px solid rgba(0, 243, 255, 0.1)' }, borderTop: { xs: '1px solid rgba(0, 243, 255, 0.1)', md: 'none' }, overflow: 'hidden' }}>
                <TableContainer sx={{ flexGrow: 1, overflow: 'auto', width: '100%', '&::-webkit-scrollbar': { width: 4 }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(0, 243, 255, 0.2)', borderRadius: 4 } }}>
                    <Table size="small" stickyHeader sx={{ width: '100%' }}>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{ bgcolor: 'rgba(5,5,15,0.98)', borderBottom: '2px solid #7000ff', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800, fontFamily: 'Orbitron', py: 1.5, width: '100%' }}>
                                    COUNTRY
                                </TableCell>
                                <TableCell align="right" sx={{ bgcolor: 'rgba(5,5,15,0.98)', borderBottom: '2px solid #7000ff', color: '#7000ff', fontSize: '0.7rem', fontWeight: 800, fontFamily: 'Orbitron', py: 1.5 }}>
                                    COUNT
                                </TableCell>
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
                                                    component="img"
                                                    src={`https://flagcdn.com/w20/${country.iso.toLowerCase()}.png`}
                                                    alt={country.name}
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
            </Box>
        </Box>
    );

    if (disableCard) {
        return content;
    }

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
                {content}
            </CardContent>
        </Card>
    );
};