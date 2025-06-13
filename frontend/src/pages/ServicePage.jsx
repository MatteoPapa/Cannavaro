import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Container,
  Typography,
  Box,
  Button,
  Stack,
  Card,
  CardContent,
  Chip,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useAlert } from "../context/AlertContext";
import ServiceHeader from "../components/ServiceHeader";
import RestartingDocker from "../assets/RestartingDocker";
import DockerLogo from "../assets/DockerLogo";
import ElectricalServicesIcon from "@mui/icons-material/ElectricalServices";
import IconButton from "@mui/material/IconButton";
import LockOutlineIcon from "@mui/icons-material/LockOutline";
import LockOpenIcon from "@mui/icons-material/LockOpen";

function ServicePage() {
  const { name } = useParams();
  const { showAlert } = useAlert();
  const [service, setService] = useState(null);
  const [restartingDocker, setRestartingDocker] = useState(false);
  const [lockedServices, setLockedServices] = useState(new Set());

  useEffect(() => {
    if (!name) return;

    // Fetch service details
    fetch("/api/services")
      .then((res) => res.json())
      .then((services) => {
        const found = services.find((s) => s.name === name);
        setService(found);
      });

    // Fetch locked services
    fetch(`/api/service_locks?parent=${name}`)
      .then((res) => res.json())
      .then((data) => {
        setLockedServices(new Set(data.locked || []));
      });
  }, [name]);

  const handleLockToggle = async (serviceName) => {
    const isLocked = lockedServices.has(serviceName);
    const newLocked = new Set(lockedServices);
    isLocked ? newLocked.delete(serviceName) : newLocked.add(serviceName);
    setLockedServices(newLocked);

    try {
      const res = await fetch("/api/service_locks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent: name,
          service: serviceName,
          lock: !isLocked,
        }),
      });
      const data = await res.json();
      setLockedServices(new Set(data.locked || []));
    } catch (err) {
      showAlert("Error updating lock state: " + err.message, "error");
    }
  };

  const handleResetDocker = async () => {
    setRestartingDocker(true);
    try {
      const res = await fetch("/api/reset_docker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: service.name,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Unknown error");
      }

      showAlert("Docker reset successfully", "success");
    } catch (err) {
      showAlert("Error resetting Docker: " + err.message, "error");
    } finally {
      setRestartingDocker(false);
    }
  };

  if (!service) {
    return (
      <Typography sx={{ m: 4 }}>Loading or service not found...</Typography>
    );
  }

  return (
    <Container display="flex" maxWidth="md">
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          position: "absolute",
        }}
        mb={2}
      >
        <Button
          component={Link}
          to="/"
          color="action"
          sx={{
            mb: 2,
            ":hover": {
              backgroundColor: "action.hover",
              color: "text.primary",
            },
          }}
        >
          <ArrowBackIcon sx={{ mr: 1 }} fontSize="large" />
          Back
        </Button>
      </Box>

      <ServiceHeader service={service} />

      {restartingDocker ? (
        <RestartingDocker />
      ) : (
        <Box display={"flex"} justifyContent="center" gap={2}>
          <Button variant="outlined" onClick={handleResetDocker}>
            <DockerLogo size={25} mr={4} />
            Restart Full Docker
          </Button>
        </Box>
      )}
      <Typography
        variant="h6"
        align="center"
        sx={{ mt: 4, fontWeight: 600, letterSpacing: 1 }}
      >
        All Services:
      </Typography>
      <Stack spacing={2} width="100%" alignItems="center" mt={2}>
        {service.services.map((service) => (
          <Card
            key={service}
            variant="outlined"
            sx={{
              width: "100%",
              maxWidth: 500,
              textDecoration: "none",
              bgcolor: "background.paper",
              color: "text.primary",
              transition: "0.3s",
              borderRadius: 2,
              p: 2,
              "&:hover": {
                boxShadow: 6,
              },
            }}
          >
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
                mb={1}
              >
                {/* Left side: icon + name */}
                <Box display="flex" alignItems="center" gap={1}>
                  <ElectricalServicesIcon fontSize="medium" color="primary" />
                  <Typography variant="h6">
                    {service.charAt(0).toUpperCase() + service.slice(1)}
                  </Typography>
                </Box>

                {/* Right side: Lock icon */}
                <Box mr={2}>
                  <IconButton onClick={() => handleLockToggle(service)}>
                    {lockedServices.has(service) ? (
                      <LockOutlineIcon
                        fontSize={"large"}
                        sx={{ color: "red" }}
                      />
                    ) : (
                      <LockOpenIcon fontSize={"large"} />
                    )}
                  </IconButton>
                </Box>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}

export default ServicePage;
