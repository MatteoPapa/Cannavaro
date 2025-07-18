import {
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  RadioGroup,
  Radio,
} from "@mui/material";
import ElectricalServicesIcon from "@mui/icons-material/ElectricalServices";
import LockOutlineIcon from "@mui/icons-material/LockOutline";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import ShieldIcon from "@mui/icons-material/Shield";
import InfoWithDetails from "../assets/InfoWithDetails";
import ProxyInstallDialog from "../assets/ProxyInstallDialog"; // adjust path as needed


import { useState } from "react";

function SubserviceCard({
  parent,
  service,
  isLocked,
  onToggleLock,
  onRestart,
  settingProxy,
  setSettingProxy,
  setServiceIsProxy,
}) {
  const [dialogOpen, setDialogOpen] = useState(false);
  return (
    <>
      <Card
        variant="outlined"
        sx={{
          width: "100%",
          minWidth: 500,
          bgcolor: "background.paper",
          borderRadius: 2,
          border: "none",
          boxShadow: 6,
        }}
      >
        <CardContent>
          <Box display="flex" gap={2}>
            <Box display="flex" alignItems="center" justifyContent="center">
              <IconButton onClick={() => onToggleLock(service.name)}>
                {isLocked ? (
                  <Tooltip title="The service will not be restarted">
                    <LockOutlineIcon fontSize="large" sx={{ color: "red" }} />
                  </Tooltip>
                ) : (
                  <Tooltip title="The service will be restarted">
                    <LockOpenIcon fontSize="large" />
                  </Tooltip>
                )}
              </IconButton>
            </Box>

            <Box flexGrow={1}>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="h6">
                    {service.name.charAt(0).toUpperCase() +
                      service.name.slice(1)}
                  </Typography>
                  <InfoWithDetails service={service} />
                </Box>

                <Box>
                  <IconButton
                    onClick={() => onRestart(service.name)}
                    disabled={isLocked}
                    color="primary"
                  >
                    <Tooltip title="Restart this subservice only">
                      <RestartAltIcon fontSize="large" />
                    </Tooltip>
                  </IconButton>
                  <IconButton
                    onClick={() => setDialogOpen(true)}
                    disabled={isLocked || settingProxy}
                    color="secondary"
                  >
                    <Tooltip title="Install proxy on this service">
                      <ShieldIcon fontSize="large" />
                    </Tooltip>
                  </IconButton>
                </Box>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <ProxyInstallDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        parent={parent.name}
        subservice={service.name}
        setSettingProxy={setSettingProxy}
        setServiceIsProxy={setServiceIsProxy}
      />


    </>
  );
}

export default SubserviceCard;
