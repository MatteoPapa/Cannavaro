import { Box, Button, CircularProgress } from "@mui/material";
import DockerLogo from "../assets/DockerLogo";
import GitLogo from "../assets/GitLogo";

function DockerActionsBar({ restarting, settingProxy, onRestart, onCopy }) {
  return (
    <Box display="flex" width="100%" justifyContent="center" flexDirection="row" gap={2}>
      {restarting || settingProxy ? (
        <Button variant="outlined" onClick={onRestart} sx={{ flex: 1 }} disabled>
          <CircularProgress size={20} sx={{ mr: 1 }} />
          {settingProxy ? "Setting Proxy..." : "Restarting Docker..."}
        </Button>
      ) : (
        <Button variant="outlined" onClick={onRestart} sx={{ flex: 1 }}>
          <DockerLogo size={25} mr={4} />
          Restart Full Docker
        </Button>
      )}

      <Button variant="outlined" color="success" onClick={onCopy} sx={{ flex: 1 }}>
        <GitLogo size={20} mr={5} />
        Copy Git Clone Command
      </Button>
    </Box>
  );
}

export default DockerActionsBar;
