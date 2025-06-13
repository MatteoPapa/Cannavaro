import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Divider,
  Box
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const DetailsMenu = ({ name, list }) => {
  if (!list || (Array.isArray(list) && list.length === 0) || (typeof list === 'object' && !Array.isArray(list) && Object.keys(list).length === 0)) {
    return null;
  }

  // Flatten object to list of key=value strings if needed
  const flattenedList = Array.isArray(list)
    ? list
    : Object.entries(list).map(([key, value]) => `${key}=${value}`);

  return (
    <Accordion sx={{ mt: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography>{name}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {flattenedList.map((item, i) => (
          <Box key={i} sx={{ m: 1 }} display="flex" flexDirection="column" gap={1}>
            {i !== 0 && <Divider />}
            <Typography variant="body2" component="code" sx={{ fontFamily: 'monospace' }}>
              {item}
            </Typography>
          </Box>
        ))}
      </AccordionDetails>
    </Accordion>
  );
};

export default DetailsMenu;
