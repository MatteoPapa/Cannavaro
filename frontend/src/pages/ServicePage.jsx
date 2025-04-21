import { Link, useParams } from "react-router-dom";
import { useEffect, useState, useRef } from "react";
import { Container, Typography, Box, Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import HistoryIcon from "@mui/icons-material/History";

import PatchCard from "../components/PatchCard";
import UploadPatchDialog from "../components/UploadPatchDialog";
import ServiceHeader from "../components/ServiceHeader";
import DropZone from "../components/DropZone";

function ServicePage() {
  const { name } = useParams();
  const [service, setService] = useState(null);
  const [patches, setPatches] = useState([]);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [description, setDescription] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef();

  useEffect(() => {
    fetch("/api/services")
      .then((res) => res.json())
      .then((services) => {
        const found = services.find((s) => s.name === name);
        setService(found);
        if (found) {
          fetch(`/api/patches/${found.name}`)
            .then((res) => res.json())
            .then((data) => setPatches(data));
        }
      });
  }, [name]);

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

  const handleUpload = async () => {
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

      const updated = await fetch(`/api/patches/${service.name}`).then((r) =>
        r.json()
      );
      setPatches(updated);
      setDescription("");
      setSelectedFile(null);
      setUploadDialogOpen(false);
    } catch (err) {
      console.error("Upload error:", err);
    }
  };

  if (!service)
    return <Typography sx={{ m: 4 }}>Loading or service not found...</Typography>;

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box sx={{ display: "flex", justifyContent: "center" }}>
        <Button component={Link} to="/" color="action">
          <ArrowBackIcon sx={{ mr: 1 }} />
          Back
        </Button>
      </Box>

      <ServiceHeader service={service} onUploadClick={handleUploadClick} />

      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <DropZone
        onFileDrop={(file) => {
          setSelectedFile(file);
          setUploadDialogOpen(true);
        }}
        isDragging={isDragging}
        setIsDragging={setIsDragging}
      />

      <Typography variant="h5" sx={{ mt: 5 }}>
        <HistoryIcon sx={{ verticalAlign: "middle", mr: 1 }} color="primary" />
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
          {patches.map((patch) => (
            <PatchCard key={patch.id} patch={patch} />
          ))}
        </Box>
      )}

      <UploadPatchDialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onUpload={handleUpload}
        description={description}
        setDescription={setDescription}
      />
    </Container>
  );
}

export default ServicePage;
