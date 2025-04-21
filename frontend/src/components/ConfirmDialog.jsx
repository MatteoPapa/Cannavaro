import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
  } from "@mui/material";
  
  export default function ConfirmDialog({ open, onClose, onConfirm, title, description }) {
    return (
      <Dialog open={open} onClose={onClose}>
        <DialogTitle sx={{
            textAlign: "center",
            fontSize: "1.3rem",
            fontWeight: "bold",
        }}>{title}</DialogTitle>
        <DialogContent>
          <Typography>{description}</Typography>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={onConfirm} color="primary" variant="contained">
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    );
  }
  