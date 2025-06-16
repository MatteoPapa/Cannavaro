import {
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Box,
  Typography,
} from "@mui/material";
import ElectricalServicesIcon from "@mui/icons-material/ElectricalServices";
import LockOutlineIcon from "@mui/icons-material/LockOutline";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import ShieldIcon from "@mui/icons-material/Shield";
import DetailsMenu from "./DetailsMenu";

function SubserviceCard({
  service,
  isLocked,
  onToggleLock,
  onRestart,
  onInstallProxy,
  isInstallingProxy
}) {
  return (
    <Card
      variant="outlined"
      sx={{
        width: "100%",
        maxWidth: 500,
        bgcolor: "background.paper",
        borderRadius: 2,
        border: "none",
        boxShadow: 6,
      }}
    >
      <CardContent>
        <Box display="flex" gap={2}>
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

          <Box flexGrow={1}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box display="flex" alignItems="center" gap={1}>
                <ElectricalServicesIcon fontSize="medium" color="primary" />
                <Typography variant="h6">
                  {service.name.charAt(0).toUpperCase() + service.name.slice(1)}
                </Typography>
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
                  onClick={() => onInstallProxy(service.name)}
                  disabled={isLocked || isInstallingProxy}
                  color="secondary"
                >
                  <Tooltip title="Install proxy on this service">
                    <ShieldIcon fontSize="large" />
                  </Tooltip>
                </IconButton>
              </Box>
            </Box>
            <Box>
              <DetailsMenu name="Environment" list={service.environment} />
              <DetailsMenu name="Mounted Volumes" list={service.volumes} />
              <DetailsMenu name="Exposed Ports" list={service.ports} />
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default SubserviceCard;
