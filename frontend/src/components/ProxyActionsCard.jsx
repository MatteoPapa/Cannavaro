import { useState } from "react";
import {
  Card,
  CardContent,
  Box,
  Button,
  Tabs,
  Tab,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import CachedIcon from "@mui/icons-material/Cached";
import RegexEditor from "./RegexEditor";

import Editor from "@monaco-editor/react";

function TabPanel({ children, value, index }) {
  return value === index ? (
    <Box mt={2}>
      {children}
    </Box>
  ) : null;
}

function ProxyActionsCard({ onSave, onReload }) {
  const [tabIndex, setTabIndex] = useState(0);
  const [code, setCode] = useState(`import socket

def handle_connection(conn):
    data = conn.recv(1024)
    print("Received:", data)
    conn.sendall(b'Hello back!')

s = socket.socket()
s.bind(('0.0.0.0', 8080))
s.listen(5)
while True:
    conn, addr = s.accept()
    handle_connection(conn)
    conn.close()`);

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
          <RegexEditor />
        </TabPanel>

        <TabPanel value={tabIndex} index={1}>
          <Editor
            height="400px"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(value) => setCode(value)}
            options={{
              fontSize: 12,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
            }}
          />
        </TabPanel>
      </CardContent>
    </Card>
  );
}

export default ProxyActionsCard;
