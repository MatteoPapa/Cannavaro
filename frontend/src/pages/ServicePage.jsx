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
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import Tooltip from "@mui/material/Tooltip";
import ShieldIcon from "@mui/icons-material/Shield";
import CircularProgress from "@mui/material/CircularProgress";
import ConfirmDialog from "../components/ConfirmDialog";
import SaveIcon from "@mui/icons-material/Save";
import CachedIcon from "@mui/icons-material/Cached";
import SubserviceCard from "../components/SubserviceCard";
import DockerActionsBar from "../components/DockerActionsBar";
import ProxyActionsCard from "../components/ProxyActionsCard";

function ServicePage() {
  const { name } = useParams();
  const { showAlert } = useAlert();
  const [service, setService] = useState(null);
  const [settingProxy, setSettingProxy] = useState(false);
  const [restartingDocker, setRestartingDocker] = useState(false);
  const [lockedServices, setLockedServices] = useState(new Set());
  const [vmIp, setVmIp] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSubservice, setPendingSubservice] = useState(null);

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

  const copyGitClone = (service, vmIp) => {
    // New copy function <---------- Supported over HTTP
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
  };

  const triggerInstallProxy = (subservice) => {
    setConfirmOpen(true);
    setPendingSubservice(subservice);
  };

  const handleConfirmInstall = async () => {
    setConfirmOpen(false);
    if (!pendingSubservice) return;

    setSettingProxy(true);
    try {
      const res = await fetch("/api/install_proxy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: name,
          subservice: pendingSubservice,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Unknown error");

      showAlert(`Proxy installed for ${pendingSubservice}`, "success");
    } catch (err) {
      showAlert(`Failed to install proxy: ${err.message}`, "error");
    } finally {
      setSettingProxy(false);
      setPendingSubservice(null);
    }
  };

  if (!service) {
    return (
      <Container display="flex">
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container display="flex" maxWidth="lg">
      <Box display="flex" alignItems="center" position="relative" mb={2}>
        {/* Back Button: aligned left */}
        <Box position="absolute" left={0}>
          <Button
            component={Link}
            to="/"
            color="action"
            sx={{
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

        {/* ServiceHeader: centered */}
        <Box mx="auto">
          <ServiceHeader service={service} />
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box
        display="flex"
        justifyContent="center"
        flexDirection="column"
        mb={2}
        gap={2}
      >
        <Card
          variant="outlined"
          sx={{ flex: 1, borderRadius: 2, boxShadow: 6 }}
        >
          <CardContent>
            <DockerActionsBar
              restarting={restartingDocker}
              settingProxy={settingProxy}
              onRestart={handleResetDocker}
              onCopy={() => copyGitClone(service.name, vmIp)}
            />

            <Box display="flex" flexWrap="wrap" gap={2} mt={4}>
              {service.services.map((svc) => (
                <>
                  <Box key={svc.name} flex={0.5}>
                    <SubserviceCard
                      service={svc}
                      isLocked={lockedServices.has(svc.name)}
                      onToggleLock={handleLockToggle}
                      onRestart={handleResetSubservice}
                      onInstallProxy={triggerInstallProxy}
                      isInstallingProxy={settingProxy}
                    />
                  </Box>
                </>
              ))}
            </Box>
          </CardContent>
        </Card>

        <ProxyActionsCard
          showAlert={showAlert}
          service={service}
        />
      </Box>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirmInstall}
        title="Install Proxy"
        description={`Are you sure you want to install a proxy on "${pendingSubservice}"?`}
      />
    </Container>
  );
}

export default ServicePage;
