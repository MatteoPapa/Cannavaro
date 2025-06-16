import { Box, Typography, Chip, Button } from "@mui/material";
import FileUploadIcon from "@mui/icons-material/FileUpload";

function ServiceHeader({ service}) {
  return (
    <Box display="flex" alignItems="center" justifyContent="center" flexDirection="column" gap={3} sx={{ mb: 2 }}>
      <Typography variant="h3" color="primary">
        {service.name} <Chip title="Service Port" label={`${service.port}`} variant="outlined" />
      </Typography>
    </Box>
  );
}

export default ServiceHeader;
