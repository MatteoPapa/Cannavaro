import { Link, useParams } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
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
import FileUploadIcon from "@mui/icons-material/FileUpload";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from "@mui/material";

function ServicePage() {
  const { name } = useParams();
  const [service, setService] = useState(null);
  const [patches, setPatches] = useState([]);

  useEffect(() => {
    // Fetch service info
    fetch("/api/services")
      .then((res) => res.json())
      .then((services) => {
        const found = services.find((s) => s.name === name);
        setService(found);

        // Fetch patches only if service is found
        if (found) {
          fetch(`/api/patches/${found.name}`)
            .then((res) => res.json())
            .then((data) => setPatches(data))
            .catch((err) => console.error("Error fetching patches:", err));
        }
      });
  }, [name]);

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [description, setDescription] = useState("");

  const fileInputRef = useRef();

  const handleUploadClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadDialogOpen(true);
    }
  };

  if (!service)
    return (
      <Typography sx={{ m: 4 }}>Loading or service not found...</Typography>
    );

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Button component={Link} to="/" color="action">
          <ArrowBackIcon sx={{ mr: 1 }} />
          Back
        </Button>
      </Box>

      <Box
        display={"flex"}
        alignItems="center"
        justifyContent="center"
        flexDirection={"column"}
        gap={3}
        sx={{ mb: 3 }}
      >
        <Typography variant="h3" color="primary">
          {service.name} <Chip label={`${service.port}`} variant="outlined" />
        </Typography>
        <Button
          variant={"contained"}
          color="success"
          onClick={handleUploadClick}
        >
          <FileUploadIcon sx={{ mr: 1 }} />
          Upload Patch
        </Button>

        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        <Typography variant="h5">
          <HistoryIcon
            sx={{ verticalAlign: "middle", mr: 1 }}
            color="primary"
          />
          Patch History
        </Typography>
      </Box>

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
          {patches.map((patch) => (
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
                      <Typography variant="body1">
                        {patch.description}
                      </Typography>
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
          ))}
        </Box>
      )}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
      >
        <DialogTitle>Upload Patch for {service?.name}</DialogTitle>
        <DialogContent sx={{ minWidth: 600 }}>
          <TextField
            autoFocus
            margin="dense"
            label="Description"
            fullWidth
            multiline
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={async () => {
              if (!selectedFile || !description) return;

              const formData = new FormData();
              formData.append("file", selectedFile);
              formData.append("description", description);
              formData.append("service", service.name);

              try {
                const res = await fetch("/api/upload_patch", {
                  method: "POST",
                  body: formData,
                });

                if (!res.ok) throw new Error("Upload failed");
                // eslint-disable-next-line no-unused-vars
                const result = await res.json();

                // refresh patch list
                const updatedPatches = await fetch(
                  `/api/patches/${service.name}`
                ).then((r) => r.json());
                setPatches(updatedPatches);

                // reset UI
                setDescription("");
                setSelectedFile(null);
                setUploadDialogOpen(false);
              } catch (err) {
                console.error("Upload error:", err);
              }
            }}
          >
            Upload
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default ServicePage;
