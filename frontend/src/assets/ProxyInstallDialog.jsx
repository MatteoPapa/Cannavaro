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
} from "@mui/material";

function ProxyInstallDialog({
    open,
    onClose,
    onSubmit,
    port,
    setPort,
    useTLS,
    setUseTLS,
    serverCert,
    setServerCert,
    serverKey,
    setServerKey,
    protocol,
    setProtocol,
    service
}) {
    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle sx={{ fontSize: "1.1rem" }}>
                <Typography variant="h6" component="span" sx={{ fontWeight: "bold" }}>
                    Proxy Options
                </Typography>
            </DialogTitle>
            <DialogContent sx={{ px: 2 , py: 1 }}>

                <Box display="flex" flexDirection="column" gap={1} pt={1}>
                    <RadioGroup
                        row
                        value={protocol}
                        onChange={(e) => setProtocol(e.target.value)}
                    >
                        <FormControlLabel value="http" control={<Radio size="small" />} label="HTTP" />
                        <FormControlLabel value="tcp" control={<Radio size="small" />} label="TCP" />
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
                        sx={{
                            width: "fit-content",
                        }}
                        label="Enable TLS"
                    />
                    {useTLS && (
                        <>
                            <TextField
                                label="Server Certificate Path"
                                size="small"
                                value={serverCert}
                                onChange={(e) => setServerCert(e.target.value)}
                                defaultValue={"/root/" + service.name + "/server-cert.pem"}
                                sx={{ mb: 1 }}
                            />
                            <TextField
                                label="Server Key Path"
                                size="small"
                                value={serverKey}
                                onChange={(e) => setServerKey(e.target.value)}
                                defaultValue={"/root/" + service.name + "/server-key.pem"}
                            />
                        </>
                    )}
                </Box>
            </DialogContent>
            <DialogActions sx={{ px: 2, pb: 2 }}>
                <Button onClick={onClose} color="error">Cancel</Button>
                <Button
                    variant="contained"
                    onClick={onSubmit}
                    color="success"
                >
                    Install
                </Button>
            </DialogActions>
        </Dialog>
    );
}

export default ProxyInstallDialog;
