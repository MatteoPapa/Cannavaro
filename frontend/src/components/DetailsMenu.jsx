import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Divider,
  Box,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const DetailsMenu = ({ name, list }) => {
  if (
    !list ||
    (Array.isArray(list) && list.length === 0) ||
    (typeof list === 'object' &&
      !Array.isArray(list) &&
      Object.keys(list).length === 0)
  ) {
    return null;
  }

  // Normalize to array of strings
  const flattenedList = Array.isArray(list)
    ? list
    : Object.entries(list).map(([key, value]) => `${key}=${value}`);

  return (
    <Accordion sx={{ mt: 2, width: '100%' }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight="bold">{name}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Box display="flex" flexDirection="column" width="100%">
          {flattenedList.map((item, i) => (
            <React.Fragment key={i}>
              {i !== 0 && <Divider sx={{ my: 1 }} />}
              <Typography
                variant="body2"
                component="code"
                sx={{
                  fontFamily: 'monospace',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {item}
              </Typography>
            </React.Fragment>
          ))}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
};

export default DetailsMenu;
