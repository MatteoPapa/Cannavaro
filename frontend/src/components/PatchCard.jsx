import {
  Card,
  CardContent,
  Typography,
  Box,
  Divider,
  Button,
  Chip,
} from "@mui/material";
import BugReportIcon from "@mui/icons-material/BugReport";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { useState } from "react";
import ConfirmDialog from "./ConfirmDialog";
import { useAlert } from "../context/AlertContext";

export default function PatchCard({
  patch,
  refetch,
  isFirst,
  isConfirmed,
  setRestartingDocker,
}) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [actionType, setActionType] = useState(null); // 'delete' or 'confirm'
  const { showAlert } = useAlert();

  const handleAction = (type) => {
    document.activeElement?.blur();
    setActionType(type);
    setDialogOpen(true);
  };

  const handleConfirm = async () => {
    setDialogOpen(false);

    let usedRestart = false;

    try {
      if (actionType === "delete") {
        setRestartingDocker(true);
        usedRestart = true;

        const res = await fetch(`/api/revert_patch/${patch.id}`, {
          method: "POST",
        });
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.error || "Revert failed");
      } else if (actionType === "confirm") {
        const res = await fetch(`/api/confirm_patch/${patch.id}`, {
          method: "POST",
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Confirmation failed");
      }

      refetch();
    } catch (err) {
      showAlert({
        message: err.message || "An error occurred",
        severity: "error",
      });
    } finally {
      if (usedRestart) setRestartingDocker(false);
    }
  };

  return (
    <Box key={patch.id} sx={{ position: "relative", mb: 3 }}>
      <Box
        sx={{
          position: "absolute",
          top: 18,
          left: -4,
          width: 12,
          height: 12,
          bgcolor: "primary.main",
          borderRadius: "50%",
        }}
      />
      <Card
        variant="outlined"
        sx={{
          borderRadius: 2,
          px: 2,
          py: 1.5,
          ml: 3,
          transition: "0.2s",
        }}
      >
        <CardContent>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            gap={1}
            mb={1}
          >
            <Box display="flex" alignItems="center" gap={1} maxWidth={"70%"}>
              <BugReportIcon color="primary" />
              <Typography variant="body1" textAlign={"left"}>{patch.description}</Typography>
              <Chip
                label={patch.status?.toUpperCase() || "UNKNOWN"}
                variant="outlined"
                color={
                  patch.status === "confirmed"
                    ? "success"
                    : patch.status === "pending"
                    ? "warning"
                    : "default"
                }
                sx={{ ml: 1 }}
              />
            </Box>

            <Box display="flex" gap={1}>
              {isFirst && (
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  onClick={() => handleAction("delete")}
                >
                  DELETE
                </Button>
              )}

              {!isConfirmed && (
                <Button
                  size="small"
                  variant="outlined"
                  color="success"
                  onClick={() => handleAction("confirm")}
                >
                  CONFIRM
                </Button>
              )}
            </Box>
          </Box>

          <Divider sx={{ my: 1 }} />
          <Box display="flex" alignItems="center" gap={1}>
            <AccessTimeIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {new Date(patch.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </Typography>
          </Box>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          document.activeElement?.blur(); // 👈 optional: clear lingering focus
        }}
        onConfirm={handleConfirm}
        title={
          actionType === "delete" ? "Confirm Delete" : "Confirm Patch Action"
        }
        description={
          actionType === "delete"
            ? "Are you sure you want to delete this patch?"
            : "Are you sure you want to confirm and apply this patch?"
        }
      />
    </Box>
  );
}
