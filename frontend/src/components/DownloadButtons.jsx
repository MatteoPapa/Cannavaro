import React from "react";
import { Button, Box } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { useAlert } from "../context/AlertContext";

export default function DownloadButtons() {
  const { showAlert } = useAlert();

  const handleDownload = (url, filename) => {
    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to download from ${url}`);
        }
        return response.blob();
      })
      .then((blob) => {
        const blobUrl = window.URL.createObjectURL(new Blob([blob]));
        const link = document.createElement("a");
        link.href = blobUrl;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((error) => {
        console.error("Download error:", error);
        showAlert(`Error downloading from ${url}`, "error");
      });
  };

  return (
    <Box display={"flex"} justifyContent="center" mb={2} gap={2}>
      <Button
        variant="contained"
        color="primary"
        sx={{ mb: 2 }}
        onClick={() => handleDownload("/api/get_startup_zip", "home_backup_startup.zip")}
      >
        <DownloadIcon sx={{ mr: 1 }} />
        Original Zip
      </Button>

      <Button
        variant="contained"
        color="secondary"
        sx={{ mb: 2 }}
        onClick={() => handleDownload("/api/get_current_zip", `home_backup_${Date.now()}.zip`)}
      >
        <DownloadIcon sx={{ mr: 1 }} />
        Current Zip
      </Button>
    </Box>
  );
}
