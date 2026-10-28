package com.example.appforlpg.ui.customer

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.appforlpg.domain.model.SupportTicket

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SupportScreen(
    tickets: List<SupportTicket>,
    isKannada: Boolean,
    onSubmit: (String, String) -> Unit,
    onEscalate: (Int) -> Unit
) {
    var showNewIssueDialog by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = if (isKannada) "ಬೆಂಬಲ ಮತ್ತು ಸಹಾಯ" else "Help & Support",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            Button(onClick = { showNewIssueDialog = true }) {
                Icon(Icons.Default.SupportAgent, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(if (isKannada) "ಸಮಸ್ಯೆ ತಿಳಿಸಿ" else "Raise Issue")
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (tickets.isEmpty()) {
            EmptyStateCard(if (isKannada) "ಯಾವುದೇ ದೂರುಗಳು ಕಂಡುಬಂದಿಲ್ಲ." else "No active support issues.")
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                items(tickets) { ticket ->
                    SupportTicketCard(ticket, isKannada, onEscalate)
                }
            }
        }
    }

    if (showNewIssueDialog) {
        var selectedCategory by remember { mutableStateOf("Delivery Issue") }
        var description by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showNewIssueDialog = false },
            title = { Text(if (isKannada) "ಸಮಸ್ಯೆ ತಿಳಿಸಿ" else "Raise an Issue") },
            text = {
                Column {
                    Text(if (isKannada) "ವರ್ಗ" else "Category:")
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = selectedCategory == "Delivery Issue",
                            onClick = { selectedCategory = "Delivery Issue" },
                            label = { Text(if (isKannada) "ವಿತರಣೆ" else "Delivery") }
                        )
                        FilterChip(
                            selected = selectedCategory == "Payment Issue",
                            onClick = { selectedCategory = "Payment Issue" },
                            label = { Text(if (isKannada) "ಪಾವತಿ" else "Payment") }
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = description,
                        onValueChange = { description = it },
                        label = { Text(if (isKannada) "ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ" else "Describe the problem") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3
                    )
                }
            },
            confirmButton = {
                Button(onClick = {
                    onSubmit(selectedCategory, description)
                    showNewIssueDialog = false
                }) {
                    Text(if (isKannada) "ಸಲ್ಲಿಸಿ" else "Submit")
                }
            },
            dismissButton = {
                TextButton(onClick = { showNewIssueDialog = false }) {
                    Text(if (isKannada) "ರದ್ದುಮಾಡಿ" else "Cancel")
                }
            }
        )
    }
}

@Composable
fun SupportTicketCard(ticket: SupportTicket, isKannada: Boolean, onEscalate: (Int) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(ticket.ticketNumber, fontWeight = FontWeight.Bold)
                Surface(
                    color = if (ticket.status == "RESOLVED") MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = ticket.status,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
            Text(ticket.category, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
            Text(ticket.description, style = MaterialTheme.typography.bodyMedium)

            ticket.aiResponse?.let { ai ->
                Spacer(Modifier.height(12.dp))
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.SupportAgent, contentDescription = null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
                            Spacer(Modifier.width(6.dp))
                            Text(if (isKannada) "ಎಐ (AI) ಸಹಾಯಕಿ" else "AI Assistant", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary, fontSize = 12.sp)
                        }
                        Spacer(Modifier.height(4.dp))
                        Text(ai, style = MaterialTheme.typography.bodyMedium)

                        if (ticket.status == "AI_ASSISTED" || ticket.status == "OPEN") {
                            Spacer(Modifier.height(12.dp))
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                                OutlinedButton(onClick = { onEscalate(ticket.id) }, shape = RoundedCornerShape(8.dp)) {
                                    Icon(Icons.Default.Warning, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(6.dp))
                                    Text(if (isKannada) "ಇನ್ನೂ ಸಹಾಯ ಬೇಕು" else "Still need help")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
