import { Box, Typography } from "@mui/material";

function DropZone({ onFileDrop, isDragging, setIsDragging }) {
  return (
    <Box
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setIsDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) onFileDrop(file);
      }}
      sx={{
        border: "2px dashed",
        borderColor: isDragging ? "primary.main" : "grey.400",
        borderRadius: 2,
        width: "100%",
        maxWidth: 400,
        textAlign: "center",
        py: 3,
        px: 2,
        bgcolor: isDragging ? "#202020" : "transparent",
        color: "text.secondary",
        transition: "0.2s",
      }}
    >
      <Typography variant="body2">Or drop a file here</Typography>
    </Box>
  );
}

export default DropZone;
