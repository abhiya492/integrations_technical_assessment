import { useState } from 'react';
import {
    Box,
    TextField,
    Button,
    Typography,
    CircularProgress,
    List,
    ListItem,
    ListItemText,
    Paper,
    Divider
} from '@mui/material';
import axios from 'axios';

const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
    'Hubspot': 'hubspot'  // Add HubSpot mapping
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    
    const endpoint = endpointMapping[integrationType];

    const handleLoad = async () => {
        try {
            setIsLoading(true);
            setError(null);
            
            const formData = new FormData();
            formData.append('credentials', JSON.stringify(credentials));
            
            // Use the appropriate endpoint for HubSpot
            const url = integrationType === 'Hubspot' 
                ? `http://localhost:8000/integrations/hubspot/get_hubspot_items` 
                : `http://localhost:8000/integrations/${endpoint}/load`;
                
            const response = await axios.post(url, formData);
            const data = response.data;
            setLoadedData(data);
        } catch (e) {
            setError(e?.response?.data?.detail || "Failed to load data");
            console.error("Data loading error:", e);
        } finally {
            setIsLoading(false);
        }
    }

    // Display loaded data in a more readable format
    const renderLoadedData = () => {
        if (!loadedData || loadedData.length === 0) {
            return <Typography variant="body2">No data available</Typography>;
        }

        return (
            <Paper variant="outlined" sx={{ maxHeight: 400, overflow: 'auto', p: 1 }}>
                <List dense>
                    {loadedData.map((item, index) => (
                        <Box key={item.id || index}>
                            <ListItem>
                                <ListItemText 
                                    primary={item.name || `Item ${index}`} 
                                    secondary={
                                        <Box>
                                            <Typography variant="caption" component="div">
                                                Type: {item.type || 'Unknown'}
                                            </Typography>
                                            {item.parent_id && (
                                                <Typography variant="caption" component="div">
                                                    Parent: {item.parent_id}
                                                </Typography>
                                            )}
                                            {item.id && (
                                                <Typography variant="caption" component="div">
                                                    ID: {item.id}
                                                </Typography>
                                            )}
                                        </Box>
                                    }
                                />
                            </ListItem>
                            {index < loadedData.length - 1 && <Divider />}
                        </Box>
                    ))}
                </List>
            </Paper>
        );
    }

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%' sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                    {integrationType} Data
                </Typography>
                
                {error && (
                    <Typography color="error" variant="body2" sx={{ mb: 2 }}>
                        Error: {error}
                    </Typography>
                )}
                
                {loadedData && (
                    <Box sx={{ mt: 2, mb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                            Loaded Items: {loadedData.length}
                        </Typography>
                        {renderLoadedData()}
                    </Box>
                )}
                
                <Box display="flex" gap={2}>
                    <Button
                        onClick={handleLoad}
                        sx={{ mt: 2 }}
                        variant='contained'
                        disabled={isLoading}
                        startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : null}
                    >
                        {isLoading ? 'Loading...' : 'Load Data'}
                    </Button>
                    
                    {loadedData && (
                        <Button
                            onClick={() => setLoadedData(null)}
                            sx={{ mt: 2 }}
                            variant='outlined'
                            disabled={isLoading}
                        >
                            Clear Data
                        </Button>
                    )}
                </Box>
            </Box>
        </Box>
    );
}