import { Box, CircularProgress } from "@mui/material";
import DockerLogo from "./DockerLogo";

export default function RestartingDocker() {
  return (
    <Box display={"flex"} flexDirection="column" alignItems="center" justifyContent="center">
      <DockerLogo size={80}/>
      <Box display="flex" alignItems="center" gap={2} mt={2}>
        <CircularProgress size={35} />
        <span className="text-lg font-medium">Restarting Docker...</span>
      </Box>
    </Box>
  );
}
