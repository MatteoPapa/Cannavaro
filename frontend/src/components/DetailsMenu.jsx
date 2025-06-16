import React from 'react';
import { Typography, Divider, Box } from '@mui/material';

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
    <Box display="flex" flexDirection="column" width="100%" p={1}>
      <Typography fontWeight="bold" color="primary" gutterBottom>
        {name}
      </Typography>
      {flattenedList.map((item, i) => (
        <React.Fragment key={i}>
          <Typography
            variant="body2"
            component="code"
            sx={{
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            - {item}
          </Typography>
        </React.Fragment>
      ))}
    </Box>
  );
};

export default DetailsMenu;
