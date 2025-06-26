import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  RadioGroup,
  Radio,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { useState } from "react";
import { useAlert } from "../context/AlertContext"; // adjust path as needed

function ProxyInstallDialog({
  open,
  onClose,
  parent,
  subservice,
  setSettingProxy,
  setServiceIsProxy,
}) {
  const { showAlert } = useAlert();
  const [port, setPort] = useState("");
  const [useTLS, setUseTLS] = useState(false);
  const [serverCert, setServerCert] = useState(
    `/root/${parent}/server-cert.pem`
  );
  const [serverKey, setServerKey] = useState(`/root/${parent}/server-key.pem`);
  const [protocol, setProtocol] = useState("http");
  const [dumpPcaps, setDumpPcaps] = useState(false);
  const [pcapPath, setPcapPath] = useState(`/home/user/pcap_files/service6`);
  const [proxyType, setProxyType] = useState("AngelPit");

  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setSettingProxy(true);
    onClose();
    try {
      const res = await fetch("/api/install_proxy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: parent,
          subservice: subservice,
          port,
          tlsEnabled: useTLS,
          serverCert,
          serverKey,
          protocol,
          dumpPcaps,
          pcapPath: dumpPcaps ? pcapPath : null,
          proxyType,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Unknown error");

      showAlert?.(`Proxy installed for ${subservice}`, "success");
      setServiceIsProxy(true);
      onClose();
    } catch (err) {
      showAlert?.(`Failed to install proxy: ${err.message}`, "error");
    } finally {
      setLoading(false);
      setSettingProxy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontSize: "1.1rem" }}>
        <Typography variant="h6" component="span" sx={{ fontWeight: "bold" }}>
          Proxy Options for {subservice}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ px: 2, py: 1 }}>
        <Box display="flex" flexDirection="column" gap={1} pt={1}>
          <FormControl size="small" fullWidth>
            <InputLabel id="proxy-type-label">Proxy Type</InputLabel>
            <Select
              labelId="proxy-type-label"
              value={proxyType}
              label="Proxy Type"
              onChange={(e) => setProxyType(e.target.value)}
            >
              <MenuItem value="AngelPit">AngelPit</MenuItem>
              <MenuItem value="Mini-Proxad">Mini-Proxad</MenuItem>
              <MenuItem value="DemonHill">DemonHill</MenuItem>
            </Select>
          </FormControl>

          <RadioGroup
            row
            value={protocol}
            onChange={(e) => setProtocol(e.target.value)}
          >
            <FormControlLabel
              value="http"
              control={<Radio size="small" />}
              label="HTTP"
            />
            <FormControlLabel
              value="tcp"
              control={<Radio size="small" />}
              label="TCP"
            />
          </RadioGroup>

          <TextField
            label="New Port (Optional)"
            size="small"
            value={port}
            onChange={(e) => setPort(e.target.value)}
          />

          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={useTLS}
                onChange={(e) => setUseTLS(e.target.checked)}
              />
            }
            sx={{ width: "fit-content" }}
            label="Enable TLS"
          />

          {useTLS && (
            <>
              <TextField
                label="Server Certificate Path"
                size="small"
                value={serverCert}
                onChange={(e) => setServerCert(e.target.value)}
                sx={{ mb: 1 }}
              />
              <TextField
                label="Server Key Path"
                size="small"
                value={serverKey}
                onChange={(e) => setServerKey(e.target.value)}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    size="small"
                    checked={dumpPcaps}
                    onChange={(e) => setDumpPcaps(e.target.checked)}
                  />
                }
                sx={{ width: "fit-content" }}
                label="Dump pcaps"
              />
              {dumpPcaps && (
                <TextField
                  label="PCAPs Output Path"
                  size="small"
                  value={pcapPath}
                  onChange={(e) => setPcapPath(e.target.value)}
                />
              )}
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 2, pb: 2 }}>
        <Button onClick={onClose} color="error" disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          color="success"
          disabled={loading}
        >
          {loading ? "Installing..." : "Install"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default ProxyInstallDialog;
