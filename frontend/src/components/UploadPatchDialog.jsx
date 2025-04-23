import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
} from "@mui/material";

export default function UploadPatchDialog({
  open,
  onClose,
  onUpload,
  description,
  setDescription,
}) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle
        sx={{
          textAlign: "center",
          fontSize: "1.3rem",
          fontWeight: "bold",
        }}
      >
        Choose Description
      </DialogTitle>
      <DialogContent sx={{ minWidth: 600 }}>
        <TextField
          autoFocus
          margin="dense"
          label="Description"
          fullWidth
          multiline
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onUpload();
            }
          }}
        />
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center" }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onUpload} color="primary" variant="contained">
          Upload
        </Button>
      </DialogActions>
    </Dialog>
  );
}
