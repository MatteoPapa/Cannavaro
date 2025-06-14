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
  Divider,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useAlert } from "../context/AlertContext";
import ServiceHeader from "../components/ServiceHeader";
import DetailsMenu from "../components/DetailsMenu";
import RestartingDocker from "../assets/RestartingDocker";
import DockerLogo from "../assets/DockerLogo";
import GitLogo from "../assets/GitLogo";
import ElectricalServicesIcon from "@mui/icons-material/ElectricalServices";
import IconButton from "@mui/material/IconButton";
import LockOutlineIcon from "@mui/icons-material/LockOutline";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import Tooltip from "@mui/material/Tooltip";
import { Accordion, AccordionSummary, AccordionDetails } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

function ServicePage() {
  const { name } = useParams();
  const { showAlert } = useAlert();
  const [service, setService] = useState(null);
  const [restartingDocker, setRestartingDocker] = useState(false);
  const [lockedServices, setLockedServices] = useState(new Set());
  const [vmIp, setVmIp] = useState("");

  useEffect(() => {
    if (!name) return;

    // Fetch service details
    fetch(`/api/services?name=${name}`)
      .then((res) => res.json())
      .then((service) => {
        setService(service);
      });

    // Fetch locked services
    fetch(`/api/service_locks?parent=${name}`)
      .then((res) => res.json())
      .then((data) => {
        setLockedServices(new Set(data.locked || []));
      });

    fetch("/api/vm_ip")
      .then((res) => res.json())
      .then((data) => {
        setVmIp(data);
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

  const copyGitClone = (service, vmIp) => { // New copy function <---------- Supported over HTTP 
    const text = `GIT_SSH_COMMAND='ssh -i ~/git_key.pem' git clone ssh://root@${vmIp}/root/${service}`;

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed"; // Prevents scroll jump
    textarea.style.opacity = "0"; // Hidden from view
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    try {
      const successful = document.execCommand("copy");
      if (successful) {
        showAlert("Git command copied successfully", "success");
      } else {
        showAlert("Copy failed", "error");
      }
    } catch (err) {
      showAlert(`Copy not supported: ${err.message}`, "error");
    }

    document.body.removeChild(textarea);
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

  const handleResetSubservice = async (subservice) => {
    setRestartingDocker(true);
    try {
      const res = await fetch("/api/reset_docker", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: name,
          subservice: subservice,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Unknown error");
      }

      showAlert(`Subservice ${subservice} restarted`, "success");
    } catch (err) {
      showAlert(`Failed to restart ${subservice}: ${err.message}`, "error");
    } finally {
      setRestartingDocker(false);
    }
  }

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

      <Box display={"flex"} justifyContent="center">
        <Box
          display={"flex"}
          width="fit-content"
          justifyContent="center"
          flexDirection="column"
          gap={2}
        >
          {restartingDocker ? (
            <RestartingDocker />
          ) : (
            <Button variant="outlined" onClick={handleResetDocker}>
              <DockerLogo size={25} mr={4} />
              Restart Full Docker
            </Button>
          )}

          <Button
            variant="outlined"
            color="success"
            onClick={() => copyGitClone(service.name, vmIp)}
          >
            <GitLogo size={20} mr={5} />
            Copy Git Clone Command
          </Button>
        </Box>
      </Box>

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
            key={service.name}
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
                    {service.name.charAt(0).toUpperCase() +
                      service.name.slice(1)}
                  </Typography>
                </Box>

                {/* Right side: Lock icon */}
                <Box mr={2}>
                  <IconButton onClick={() => handleLockToggle(service.name)}>
                    {lockedServices.has(service.name) ? (
                      <Tooltip title="The service will not be restarted">
                        <LockOutlineIcon
                          fontSize={"large"}
                          sx={{ color: "red" }}
                        />
                      </Tooltip>
                    ) : (
                      <Tooltip title="The service will be restarted">
                        <LockOpenIcon fontSize={"large"} />
                      </Tooltip>
                    )}
                  </IconButton>
                  <IconButton
                    onClick={() => handleResetSubservice(service.name)}
                    disabled={lockedServices.has(service.name)}
                    color =  "primary"
                  >
                    <Tooltip title="Restart this subservice only">
                      <RestartAltIcon fontSize={"large"}/>
                    </Tooltip>
                  </IconButton>
                </Box>
              </Box>

              {/* Show detailed info */}
              <DetailsMenu name="Environment" list={service.environment} />
              <DetailsMenu name="Mounted Volumes" list={service.volumes} />
              <DetailsMenu name="Exposed Ports" list={service.ports} />
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}

export default ServicePage;
