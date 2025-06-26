import { useState, useEffect, useCallback, useRef } from "react";
import {
  Card,
  CardContent,
  Box,
  Button,
  Tabs,
  Tab,
  Typography,
  CircularProgress,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import CachedIcon from "@mui/icons-material/Cached";
import RegexEditor from "./RegexEditor";
import Editor from "@monaco-editor/react";
import AnsiToHtml from "ansi-to-html";

function TabPanel({ children, value, index }) {
  return value === index ? <Box mt={2}>{children}</Box> : null;
}

function ProxyActionsCard({ showAlert, service }) {
  const [tabIndex, setTabIndex] = useState(0);
  const [code, setCode] = useState(``);
  const [regex, setRegex] = useState([]);

  const logRef = useRef(null);
  const intervalRef = useRef(null);
  const ansiConverter = new AnsiToHtml();
  const lastLogLengthRef = useRef(0);

  const refetchCodeFromServer = useRef(true);

  const handleSaveChanges = async () => {
    refetchCodeFromServer.current = false;

    if (tabIndex === 0) {
      try {
        const response = await fetch("/api/save_proxy_regex", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ service: service.name, regex }),
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Failed to save regex");

        showAlert(`Regex for ${service.name} saved successfully.`, "success");
        refetchCodeFromServer.current = true;
      } catch (err) {
        showAlert("Error saving regex: " + err.message, "error");
      }
    }

    if (tabIndex === 1) {
      try {
        const res = await fetch("/api/save_proxy_code", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ service: service.name, code }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Unknown error");

        showAlert(
          `Proxy code for ${service.name} saved successfully.`,
          "success"
        );
        refetchCodeFromServer.current = true;
      } catch (err) {
        showAlert(`Failed to save proxy code: ${err.message}`, "error");
        refetchCodeFromServer.current = false;
      }
    }
  };

  const fetchProxyLogs = useCallback(async () => {
    try {
      const response = await fetch("/api/get_proxy_logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service: service.name }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch logs");
      }

      const data = await response.json();
      const fullLog = data.logs || "";
      const lastLength = lastLogLengthRef.current;

      if (!logRef.current) {
        setTimeout(fetchProxyLogs, 10);
        return;
      }

      if (fullLog.length > lastLength && logRef.current) {
        const newLogChunk = fullLog.slice(lastLength);
        const formattedChunk = ansiConverter.toHtml(
          newLogChunk.replace(/\n/g, "<br>")
        );

        logRef.current.insertAdjacentHTML("beforeend", formattedChunk);
        logRef.current.scrollTop = logRef.current.scrollHeight;
        lastLogLengthRef.current = fullLog.length;
      }
    } catch (err) {
      console.error("Error fetching proxy logs:", err);
      showAlert(`Failed to fetch logs: ${err.message}`, "error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service.name, showAlert]);

  const fetchProxyCode = useCallback(async () => {
    try {
      const response = await fetch("/api/get_proxy_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service: service.name }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch proxy code");
      }

      const data = await response.json();
      setCode(data.code || "");
    } catch (err) {
      console.error("Error fetching proxy code:", err);
      showAlert(`Failed to fetch proxy code: ${err.message}`, "error");
      // 👇 prevent repeated retries
      refetchCodeFromServer.current = false;
    }
  }, [service.name, showAlert]);

  const fetchProxyRegex = useCallback(async () => {
    try {
      const response = await fetch("/api/get_proxy_regex", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service: service.name }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch regex");
      }

      const data = await response.json();
      setRegex(data.regex || []);
    } catch (err) {
      console.error("Error fetching proxy regex:", err);
      showAlert(`Failed to fetch regex: ${err.message}`, "error");
    }
  }, [service.name, showAlert]);

  useEffect(() => {
    if (tabIndex === 0) {
      fetchProxyRegex();
    }

    // Code tab
    if (tabIndex === 1) {
      if (refetchCodeFromServer.current) {
        fetchProxyCode();
      }
    } else {
      refetchCodeFromServer.current = true;
    }

    let interval;

    if (tabIndex === 2) {
      lastLogLengthRef.current = 0;
      if (logRef.current) {
        logRef.current.innerHTML = "";
      }

      fetchProxyLogs();

      interval = setInterval(fetchProxyLogs, 5000);
      intervalRef.current = interval;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [tabIndex, fetchProxyLogs, fetchProxyCode, fetchProxyRegex, service.name]);

  return (
    <Card
      variant="outlined"
      sx={{
        flex: 1,
        bgcolor: "background.paper",
        color: "text.primary",
        borderRadius: 2,
        boxShadow: 6,
        transition: "0.3s",
      }}
    >
      <CardContent>
        {/* Action buttons */}
        <Box display="flex" justifyContent="center" mb={2}>
          <Button
            variant="outlined"
            onClick={handleSaveChanges}
            color="secondary"
            sx={{
              width: "60%",
            }}
          >
            <CachedIcon sx={{ mr: 1 }} />
            Save & Reload Proxy
          </Button>
        </Box>

        {/* Tabs */}
        <Tabs
          value={tabIndex}
          onChange={(_, newIndex) => setTabIndex(newIndex)}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab label="BLOCKED REGEX" />
          <Tab label="FULL CODE" />
          <Tab label="PROXY LOGS" />
        </Tabs>

        {/* Tab Panels */}
        <TabPanel value={tabIndex} index={0}>
          <RegexEditor regex={regex} setRegex={setRegex} />
        </TabPanel>

        <TabPanel value={tabIndex} index={1}>
          <Editor
            height="700px"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(value) => setCode(value)}
            options={{
              fontSize: 12,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: "on",
            }}
          />
        </TabPanel>

        <TabPanel value={tabIndex} index={2}>
          <Box
            ref={logRef}
            sx={{
              fontFamily: "monospace",
              backgroundColor: "#111",
              color: "#eee",
              padding: 2,
              borderRadius: 1,
              height: "700px",
              overflowY: "auto",
              lineHeight: 1.6,
              textAlign: "left",
              fontSize: "0.9rem",
            }}
          />
        </TabPanel>
      </CardContent>
    </Card>
  );
}

export default ProxyActionsCard;
