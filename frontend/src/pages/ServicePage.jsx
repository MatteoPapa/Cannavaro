import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Container,
  Typography,
  Card,
  CardContent,
  Chip,
  Box,
  Divider,
  Button,
} from "@mui/material";
import BugReportIcon from "@mui/icons-material/BugReport";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import HistoryIcon from "@mui/icons-material/History";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

function ServicePage() {
  const { name } = useParams();
  const [service, setService] = useState(null);

  const fakePatches = [
    {
      id: 1,
      description: "Fixed remote code execution",
      timestamp: "2025-04-10 14:35",
      confirmed: false,
    },
    {
      id: 2,
      description: "Patched SQL injection",
      timestamp: "2025-03-28 09:20",
      confirmed: true,
    },
    {
      id: 3,
      description: "Updated logging mechanism",
      timestamp: "2025-03-01 17:02",
      confirmed: true,
    },
    {
      id: 4,
      description: "Cooked some spaghetti",
      timestamp: "2025-03-01 13:43",
      confirmed: true,
    },    {
      id: 5,
      description: "Watered the plants",
      timestamp: "2025-03-01 12:21",
      confirmed: true,
    },
  ];

  useEffect(() => {
    fetch("/api/services")
      .then((res) => res.json())
      .then((services) => {
        const found = services.find((s) => s.name === name);
        setService(found);
      });
  }, [name]);

  if (!service)
    return (
      <Typography sx={{ m: 4 }}>Loading or service not found...</Typography>
    );

  return (
    <Container maxWidth="md" sx={{ mt: 5 }}>
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Button component={Link} to="/" color="action">
          <ArrowBackIcon sx={{ mr: 1 }} />
          Back
        </Button>
      </Box>

      <Typography variant="h3" color="primary" sx={{ mb: 1 }}>
        {service.name} <Chip label={`${service.port}`} variant="outlined" />
      </Typography>

      <Typography variant="h5" sx={{ mb: 3, mt: 2 }}>
        <HistoryIcon sx={{ verticalAlign: "middle", mr: 1 }} color="primary" />
        Patch History
      </Typography>

      <Box
        sx={{
          position: "relative",
          pl: 3,
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 15,
            width: "2px",
            height: "100%",
            bgcolor: "primary.main",
          },
        }}
      >
        {[...fakePatches].map((patch) => (
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
                    {patch.confirmed ? (
                      <Chip
                        label="CONFIRMED"
                        size="small"
                        variant="outlined"
                        color="success"
                        sx={{ ml: 1 }}
                      />
                    ) : (
                      <Chip
                        label="PENDING"
                        size="small"
                        variant="outlined"
                        color="warning"
                        sx={{ ml: 1 }}
                      />
                    )}
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
                    {patch.timestamp}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Box>
        ))}
      </Box>
    </Container>
  );
}

export default ServicePage;
