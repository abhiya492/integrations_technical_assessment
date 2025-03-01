import { useState } from 'react';
import {
    Box,
    Autocomplete,
    TextField,
    Typography,
    Paper,
    Divider
} from '@mui/material';
import { AirtableIntegration } from './integrations/airtable';
import { NotionIntegration } from './integrations/notion';
import { HubspotIntegration } from './integrations/hubspot'; // Import HubSpot component
import { DataForm } from './data-form';

const integrationMapping = {
    'Notion': NotionIntegration,
    'Airtable': AirtableIntegration,
    'Hubspot': HubspotIntegration  // Add HubSpot mapping
};

export const IntegrationForm = () => {
    const [integrationParams, setIntegrationParams] = useState({});
    const [user, setUser] = useState('TestUser');
    const [org, setOrg] = useState('TestOrg');
    const [currType, setCurrType] = useState(null);
    const CurrIntegration = integrationMapping[currType];

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' sx={{ width: '100%', p: 3 }}>
            <Paper elevation={3} sx={{ p: 3, width: '100%', maxWidth: 600 }}>
                <Typography variant="h5" gutterBottom align="center">
                    VectorShift Integration Demo
                </Typography>
                
                <Divider sx={{ my: 2 }} />
                
                <Box display='flex' flexDirection='column'>
                    <TextField
                        label="User ID"
                        value={user}
                        onChange={(e) => setUser(e.target.value)}
                        sx={{ mt: 2 }}
                        variant="outlined"
                        fullWidth
                    />
                    <TextField
                        label="Organization ID"
                        value={org}
                        onChange={(e) => setOrg(e.target.value)}
                        sx={{ mt: 2 }}
                        variant="outlined"
                        fullWidth
                    />
                    <Autocomplete
                        id="integration-type"
                        options={Object.keys(integrationMapping)}
                        sx={{ mt: 2 }}
                        fullWidth
                        renderInput={(params) => <TextField {...params} label="Integration Type" />}
                        onChange={(e, value) => setCurrType(value)}
                        value={currType}
                    />
                </Box>
                
                {currType && 
                <Box sx={{ mt: 3 }}>
                    <Divider sx={{ my: 2 }} />
                    <CurrIntegration 
                        user={user} 
                        org={org} 
                        integrationParams={integrationParams} 
                        setIntegrationParams={setIntegrationParams} 
                    />
                </Box>
                }
                
                {integrationParams?.credentials && 
                <Box sx={{ mt: 2 }}>
                    <Divider sx={{ my: 2 }} />
                    <DataForm 
                        integrationType={integrationParams?.type} 
                        credentials={integrationParams?.credentials} 
                    />
                </Box>
                }
            </Paper>
        </Box>
    );
}