import { Box, Typography, Chip, Button } from "@mui/material";
import FileUploadIcon from "@mui/icons-material/FileUpload";

function ServiceHeader({ service, onUploadClick }) {
  return (
    <Box display="flex" alignItems="center" justifyContent="center" flexDirection="column" gap={3} sx={{ mb: 3 }}>
      <Typography variant="h3" color="primary">
        {service.name} <Chip label={`${service.port}`} variant="outlined" />
      </Typography>

      <Button variant="contained" color="secondary" onClick={onUploadClick}>
        <FileUploadIcon sx={{ mr: 1 }} />
        Upload Patch
      </Button>
    </Box>
  );
}

export default ServiceHeader;
