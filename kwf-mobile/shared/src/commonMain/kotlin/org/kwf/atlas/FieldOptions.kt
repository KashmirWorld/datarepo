package org.kwf.atlas

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.serialization.Serializable

@Serializable
data class CrsEntry(
    val id: String,
    val name: String,
    val kind: String,
    val definition: String? = null
)

@Serializable
data class PhotoAsset(
    val id: String,
    val observationId: String,
    val localPath: String,
    val mimeType: String,
    val byteCount: Long,
    val sha256: String,
    val capturedAtEpochMs: Long?,
    val position: SourceVertex? = null,
    val objectKey: String? = null,
    val uploadState: String = "pending"
)

object FieldOptions {
    val moistureUnits = listOf(
        "percent",
        "m3/m3",
        "kPa",
        "centibar"
    )

    val heightReferences = listOf(
        "unknown",
        "ellipsoidal",
        "EPSG:5703",
        "EPSG:5714",
        "EPSG:3855"
    )

    val initialCrsEntries = listOf(
        CrsEntry("EPSG:4326", "WGS 84 longitude/latitude", "geographic"),
        CrsEntry("EPSG:32615", "WGS 84 / UTM zone 15N", "projected"),
        CrsEntry("EPSG:6344", "NAD83(2011) / UTM zone 15N", "projected"),
        CrsEntry("EPSG:6411", "NAD83(2011) / Arkansas North", "projected")
    )
}

@Composable
fun FieldChoice(
    label: String,
    value: String,
    choices: List<Pair<String, String>>,
    onSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var open by remember { mutableStateOf(false) }
    var query by remember { mutableStateOf("") }

    val display = choices.firstOrNull { it.first == value }?.second
        ?: value.ifBlank { "Select" }

    Column(modifier) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        OutlinedButton(
            onClick = {
                query = ""
                open = true
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(display)
        }
    }

    if (open) {
        val filtered = choices.filter {
            query.isBlank() ||
                "${it.first} ${it.second}".contains(query, ignoreCase = true)
        }

        AlertDialog(
            onDismissRequest = { open = false },
            title = { Text(label) },
            text = {
                Column {
                    OutlinedTextField(
                        value = query,
                        onValueChange = { query = it },
                        label = { Text("Search") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    LazyColumn(modifier = Modifier.heightIn(max = 320.dp)) {
                        items(filtered, key = { it.first }) { choice ->
                            TextButton(
                                onClick = {
                                    onSelected(choice.first)
                                    open = false
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    if (choice.first == value) {
                                        "Selected: ${choice.second}"
                                    } else {
                                        choice.second
                                    }
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { open = false }) {
                    Text("Close")
                }
            }
        )
    }
}
