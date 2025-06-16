import { useState } from "react";
import {
    Box,
    Typography,
    TextField,
    IconButton,
    Chip,
    Stack,
    Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";

function RegexEditor() {
    const [regexList, setRegexList] = useState([
        `[A-Z0-9]{31}=`,
    ]);
    const [newRegex, setNewRegex] = useState("");

    const handleAdd = () => {
        const trimmed = newRegex.trim();
        if (trimmed && !regexList.includes(trimmed)) {
            setRegexList([...regexList, trimmed]);
            setNewRegex("");
        }
    };

    const handleDelete = (pattern) => {
        setRegexList(regexList.filter((r) => r !== pattern));
    };

    return (
        <Box>
            <Box display="flex" gap={1}>
                <TextField
                    label="Add new regex"
                    variant="outlined"
                    fullWidth
                    size="small"
                    value={newRegex}
                    onChange={(e) => setNewRegex(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                />
                <Tooltip title="Add regex">
                    <IconButton color="primary" onClick={handleAdd}>
                        <AddIcon />
                    </IconButton>
                </Tooltip>
            </Box>
            <Stack spacing={1} mt={2}>
                {regexList.map((pattern, index) => (
                    <Box
                        key={index}
                        display="flex"
                        alignItems="center"
                        justifyContent="space-between"
                        sx={{
                            backgroundColor: "background.default",
                            border: "1px solid",
                            borderColor: "divider",
                            borderRadius: 1,
                            px: 2,
                            py: 1,
                        }}
                    >
                        <Typography
                            variant="body2"
                            component="code"
                            sx={{ fontFamily: "monospace", color: "primary.main" }}
                        >
                            {pattern}
                        </Typography>
                        <Tooltip title="Delete regex">
                            <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleDelete(pattern)}
                            >
                                <DeleteIcon fontSize="small" />
                            </IconButton>
                        </Tooltip>
                    </Box>
                ))}
            </Stack>

        </Box>
    );
}

export default RegexEditor;
