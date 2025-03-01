// hubspot.js

import { useState, useEffect } from 'react';
import {
    Box,
    Button,
    CircularProgress,
    Typography,
    Tooltip
} from '@mui/material';
import axios from 'axios';

export const HubspotIntegration = ({ user, org, integrationParams, setIntegrationParams }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [connectionError, setConnectionError] = useState(null);

    // Function to open OAuth in a new window
    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            setConnectionError(null);
            
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/authorize`, formData);
            const authURL = response?.data;

            // Open OAuth window
            const newWindow = window.open(authURL, 'HubSpot Authorization', 'width=800, height=700');
            
            if (!newWindow) {
                throw new Error("Pop-up blocked. Please allow pop-ups for this site.");
            }

            // Polling for the window to close
            const pollTimer = window.setInterval(() => {
                if (newWindow?.closed !== false) { 
                    window.clearInterval(pollTimer);
                    handleWindowClosed();
                }
            }, 200);
        } catch (e) {
            setIsConnecting(false);
            setConnectionError(e?.response?.data?.detail || e?.message || "Connection failed");
            console.error("HubSpot connection error:", e);
        }
    }

    // Function to handle logic when the OAuth window closes
    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/credentials`, formData);
            const credentials = response.data; 
            
            if (credentials) {
                setIsConnecting(false);
                setIsConnected(true);
                setIntegrationParams(prev => ({ ...prev, credentials: credentials, type: 'Hubspot' }));
            }
        } catch (e) {
            setIsConnecting(false);
            setConnectionError(e?.response?.data?.detail || "Failed to retrieve credentials");
            console.error("HubSpot credentials error:", e);
        }
    }

    // Handle disconnection
    const handleDisconnect = () => {
        setIsConnected(false);
        setIntegrationParams(prev => ({ ...prev, credentials: null, type: null }));
    }

    // Check if credentials exist on component mount
    useEffect(() => {
        setIsConnected(integrationParams?.credentials && integrationParams?.type === 'Hubspot' ? true : false);
    }, [integrationParams]);

    return (
        <>
        <Box sx={{mt: 2, width: '100%'}}>
            <Typography variant="subtitle1" gutterBottom>
                HubSpot Integration
            </Typography>
            
            {connectionError && (
                <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                    Error: {connectionError}
                </Typography>
            )}
            
            <Box display='flex' alignItems='center' justifyContent='center' sx={{mt: 2}}>
                {!isConnected ? (
                    <Button 
                        variant='contained' 
                        onClick={handleConnectClick}
                        disabled={isConnecting}
                        startIcon={isConnecting ? <CircularProgress size={20} color="inherit" /> : null}
                        sx={{ minWidth: '200px' }}
                    >
                        {isConnecting ? 'Connecting...' : 'Connect to HubSpot'}
                    </Button>
                ) : (
                    <Box display="flex" flexDirection="column" alignItems="center">
                        <Tooltip title="Successfully connected to HubSpot">
                            <Button 
                                variant='contained' 
                                color='success'
                                sx={{ minWidth: '200px', mb: 1 }}
                                disabled
                            >
                                HubSpot Connected
                            </Button>
                        </Tooltip>
                        
                        <Button 
                            variant='outlined' 
                            color='secondary'
                            onClick={handleDisconnect}
                            size="small"
                        >
                            Disconnect
                        </Button>
                    </Box>
                )}
            </Box>
        </Box>
        </>
    );
}