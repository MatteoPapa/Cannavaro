import { useState } from "react";
import {
  Card,
  CardContent,
  Box,
  Button,
  Tabs,
  Tab,
  Typography,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import CachedIcon from "@mui/icons-material/Cached";
import RegexEditor from "./RegexEditor";

function TabPanel({ children, value, index }) {
  return value === index ? (
    <Box mt={2}>
      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
        {children}
      </Typography>
    </Box>
  ) : null;
}

function ProxyActionsCard({ onSave, onReload }) {
  const [tabIndex, setTabIndex] = useState(0);

  return (
    <Card
      variant="outlined"
      sx={{
        flex: 1,
        bgcolor: "background.paper",
        color: "text.primary",
        transition: "0.3s",
        borderRadius: 2,
        boxShadow: 6,
      }}
    >
      <CardContent>
        <Box
          display="flex"
          width="100%"
          justifyContent="center"
          flexDirection="row"
          gap={2}
          mb={2}
        >
          <Button variant="outlined" onClick={onSave} color="customGray" sx={{ flex: 1 }}>
            <SaveIcon sx={{ mr: 1 }} />
            Save Changes
          </Button>

          <Button variant="outlined" color="secondary" onClick={onReload} sx={{ flex: 1 }}>
            <CachedIcon sx={{ mr: 1 }} />
            Reload Proxy
          </Button>
        </Box>

        <Tabs
          value={tabIndex}
          onChange={(_, newIndex) => setTabIndex(newIndex)}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="BLOCKED REGEX" />
          <Tab label="FULL CODE" />
        </Tabs>

        <TabPanel value={tabIndex} index={0}>
          <RegexEditor/>
        </TabPanel>

        <TabPanel value={tabIndex} index={1}>

        </TabPanel>
      </CardContent>
    </Card>
  );
}

export default ProxyActionsCard;
