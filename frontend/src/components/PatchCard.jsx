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
  
  export default function PatchCard({ patch }) {
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
              <Box display="flex" alignItems="center" gap={1}>
                <BugReportIcon color="primary" />
                <Typography variant="body1">{patch.description}</Typography>
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
                />
              </Box>
  
              <Box display="flex" gap={1}>
                <Button size="small" variant="outlined" color="error">
                  Revert to
                </Button>
                <Button size="small" variant="contained" color="primary">
                  Action
                </Button>
              </Box>
            </Box>
  
            <Divider sx={{ my: 1 }} />
            <Box display="flex" alignItems="center" gap={1}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {new Date(patch.timestamp).toLocaleString()}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }
  