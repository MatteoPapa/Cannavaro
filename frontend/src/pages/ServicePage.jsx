import { Link, useParams } from "react-router-dom";
import { useEffect, useState, useRef, useCallback } from "react";
import { Container, Typography, Box, Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import HistoryIcon from "@mui/icons-material/History";
import { useAlert } from "../context/AlertContext";
import PatchCard from "../components/PatchCard";
import UploadPatchDialog from "../components/UploadPatchDialog";
import ServiceHeader from "../components/ServiceHeader";
import DropZone from "../components/DropZone";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import RestartingDocker from "../assets/RestartingDocker";
import DockerLogo from "../assets/DockerLogo";

function ServicePage() {
  const { name } = useParams();
  const { showAlert } = useAlert();
  const [service, setService] = useState(null);
  const [patches, setPatches] = useState([]);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [description, setDescription] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [restartingDocker, setRestartingDocker] = useState(false);

  const fileInputRef = useRef();

  const refetchPatches = useCallback(async () => {
    if (!service?.name) return;
    const updated = await fetch(`/api/patches/${service.name}`).then((r) =>
      r.json()
    );
    setPatches(updated);
  }, [service?.name]);

  useEffect(() => {
    fetch("/api/services")
      .then((res) => res.json())
      .then((services) => {
        const found = services.find((s) => s.name === name);
        setService(found);
      });
  }, [name]);

  useEffect(() => {
    if (service) {
      refetchPatches();
    }
  }, [service, refetchPatches]);

  const handleUploadClick = () => {
    document.activeElement?.blur(); // fix potential aria-hidden focus bug
    fileInputRef.current.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadDialogOpen(true);
      e.target.value = ""; // allow re-selecting same file
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !description) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("description", description);
    formData.append("service", service.name);

    try {
      setUploadDialogOpen(false); // Close dialog
      setRestartingDocker(true); // Show "restarting docker..."

      const res = await fetch("/api/upload_patch", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      await refetchPatches();
      setDescription("");
      setSelectedFile(null);
    } catch (err) {
      showAlert("Error uploading patch: " + err.message, "error");
    } finally {
      setRestartingDocker(false); // Clear message whether success or error
    }
  };

  const handleResetDocker = async () => {
    setRestartingDocker(true);
    try {
      const res = await fetch("/api/reset_docker", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ service: service.name }),
      });
      if (!res.ok) throw new Error("Docker reset failed");

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
      <Box sx={{ display: "flex", justifyContent: "center", position: "absolute" }} mb={2}>
        <Button component={Link} to="/" color="action" sx={{ mb: 2, ":hover":{
          backgroundColor: "action.hover", color: "text.primary"
        } }}>
          <ArrowBackIcon sx={{ mr: 1}} fontSize="large"/>
          Back
        </Button>
      </Box>

      <ServiceHeader service={service} />
      {restartingDocker ? (
        <RestartingDocker />
      ) : (
        <>
          <Box display={"flex"} justifyContent="center" gap={2}>
            <Button
              variant="outlined"
              onClick={handleResetDocker}
            >
              <DockerLogo size={25} mr={4} />
              Restart Docker
            </Button>

            <Button
              variant="outlined"
              color="secondary"
              onClick={handleUploadClick}
            >
              <FileUploadIcon sx={{ mr: 1 }} />
              Upload Patch
            </Button>
          </Box>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
            <DropZone
              onFileDrop={(file) => {
                setSelectedFile(file);
                setUploadDialogOpen(true);
              }}
              isDragging={isDragging}
              setIsDragging={setIsDragging}
            />
          </Box>
          <Typography variant="h5" sx={{ mt: 3, mb: 3 }} color="text.primary">
            <HistoryIcon
              sx={{ verticalAlign: "middle", mr: 1 }}
              color="primary"
            />
            Patch History
          </Typography>
          {patches.length === 0 ? (
            <Typography variant="h5" sx={{ mt: 5 }} color="text.secondary">
              No patches found.
            </Typography>
          ) : (
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
              {patches.map((patch, index) => (
                <PatchCard
                  key={patch.id}
                  patch={patch}
                  refetch={refetchPatches}
                  isFirst={index === 0}
                  isConfirmed={patch.status === "confirmed"}
                  setRestartingDocker={setRestartingDocker}
                />
              ))}
            </Box>
          )}
        </>
      )}

      <UploadPatchDialog
        open={uploadDialogOpen}
        onClose={() => {
          setUploadDialogOpen(false);
          setSelectedFile(null);
          document.activeElement?.blur(); // optional: help with a11y
        }}
        onUpload={handleUpload}
        description={description}
        setDescription={setDescription}
      />
    </Container>
  );
}

export default ServicePage;
