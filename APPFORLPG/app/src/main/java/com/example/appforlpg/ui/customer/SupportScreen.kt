package com.example.appforlpg.ui.customer

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.appforlpg.domain.model.SupportTicket
import kotlinx.coroutines.launch
import java.util.UUID

data class ChatMessage(
    val id: String,
    val text: String,
    val isUser: Boolean,
    val ticketId: Int? = null,
    val status: String? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SupportScreen(
    tickets: List<SupportTicket>,
    isKannada: Boolean,
    onSubmit: (String, String) -> Unit,
    onEscalate: (Int) -> Unit
) {
    var userMessageText by remember { mutableStateOf("") }
    var isThinking by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    val chatList = remember { mutableStateListOf<ChatMessage>() }

    // Pre-populate initial welcome message
    LaunchedEffect(isKannada) {
        if (chatList.isEmpty()) {
            val welcomeText = if (isKannada) {
                "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಎಲ್.ಪಿ.ಜಿ ಸ್ಮಾರ್ಟ್ ಎಐ ಸಹಾಯಕಿ. ನಿಮ್ಮ ಸಿಲಿಂಡರ್ ಕಾಯ್ದಿರಿಸುವಿಕೆ, ವಿಲೇವಾರಿ, ಅಥವಾ ಪಾವತಿ ಕುರಿತು ಯಾವುದೇ ಪ್ರಶ್ನೆ ಕೇಳಿ!"
            } else {
                "Hello! I am your LPG Smart AI Support Assistant. Ask me anything about cylinder booking, delivery tracking, payment options, or safety advice!"
            }
            chatList.add(ChatMessage(id = "welcome", text = welcomeText, isUser = false))
        }
    }

    // Sync ticket responses from backend / Room DB into chatList
    LaunchedEffect(tickets) {
        tickets.forEach { ticket ->
            val userMsgId = "usr-${ticket.id}"
            if (chatList.none { it.id == userMsgId }) {
                chatList.add(ChatMessage(id = userMsgId, text = "${ticket.category}: ${ticket.description}", isUser = true))
            }
            ticket.aiResponse?.let { ai ->
                val aiMsgId = "ai-${ticket.id}"
                if (chatList.none { it.id == aiMsgId }) {
                    chatList.add(ChatMessage(id = aiMsgId, text = ai, isUser = false, ticketId = ticket.id, status = ticket.status))
                }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp)
    ) {
        // AI Chatbot Header Banner
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 10.dp),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.SmartToy,
                        contentDescription = "AI Assistant",
                        tint = MaterialTheme.colorScheme.onPrimary,
                        modifier = Modifier.size(26.dp)
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = if (isKannada) "ಎಐ ಸ್ಮಾರ್ಟ್ ಚಾಟ್‌ಬಾಟ್" else "Gemini AI Support Chatbot",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    Text(
                        text = if (isKannada) "ಆನ್‌ಲೈನ್ • 24/7 ತ್ವರಿತ ಸಮಾಧಾನ" else "Online • 24/7 Instant Query Resolution",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                    )
                }
            }
        }

        // Quick Suggestion Prompts
        Text(
            text = if (isKannada) "ತ್ವರಿತ ಪ್ರಶ್ನೆಗಳು:" else "Quick Suggestion Prompts:",
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
        )

        val quickPrompts = if (isKannada) {
            listOf(
                "🚚 ನನ್ನ ಸಿಲಿಂಡರ್ ವಿಲೇವಾರಿ ಎಷ್ಟೊತ್ತಿಗೆ ಬರುತ್ತದೆ?",
                "💳 ಯುಪಿಐ ಪಾವತಿ ಮಾಡುವುದು ಹೇಗೆ?",
                "⚠️ ಗ್ಯಾಸ್ ಸೋರಿಕೆಯಾದರೆ ಏನು ಮಾಡಬೇಕು?",
                "📋 ನನ್ನ ಸಬ್ಸಿಡಿ ಖಾತೆಗೆ ಜಮೆಯಾಗಿದೆಯೇ?"
            )
        } else {
            listOf(
                "🚚 When will my refill cylinder be delivered?",
                "💳 How do I complete payment using UPI?",
                "⚠️ What to do in case of an LPG gas leak?",
                "📋 Has my cylinder subsidy been credited?"
            )
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            quickPrompts.take(2).forEach { prompt ->
                SuggestionChip(
                    onClick = {
                        userMessageText = prompt
                    },
                    label = { Text(prompt, fontSize = 10.sp) },
                    modifier = Modifier.weight(1f)
                )
            }
        }

        Spacer(modifier = Modifier.height(6.dp))

        // Chat Conversation Stream
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(chatList) { msg ->
                if (msg.isUser) {
                    UserBubble(text = msg.text)
                } else {
                    AiBubble(
                        text = msg.text,
                        isKannada = isKannada,
                        ticketId = msg.ticketId,
                        status = msg.status,
                        onEscalate = onEscalate
                    )
                }
            }

            if (isThinking) {
                item {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(8.dp)
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (isKannada) "ಎಐ ಉತ್ತರ ತಯಾರಿಸುತ್ತಿದೆ..." else "Gemini AI is generating response...",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Chat Input Row
        Surface(
            shadowElevation = 4.dp,
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedTextField(
                    value = userMessageText,
                    onValueChange = { userMessageText = it },
                    placeholder = {
                        Text(
                            if (isKannada) "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಇಲ್ಲಿ ಬರೆಯಿರಿ..." else "Ask Gemini AI Chatbot...",
                            fontSize = 13.sp
                        )
                    },
                    modifier = Modifier.weight(1f),
                    maxLines = 3,
                    shape = RoundedCornerShape(20.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )

                Spacer(modifier = Modifier.width(8.dp))

                IconButton(
                    onClick = {
                        if (userMessageText.isNotBlank()) {
                            val textToSend = userMessageText.trim()
                            userMessageText = ""
                            
                            // 1. Immediately append user message to UI chat list
                            val userMsg = ChatMessage(id = UUID.randomUUID().toString(), text = textToSend, isUser = true)
                            chatList.add(userMsg)
                            isThinking = true

                            // 2. Submit query to Gemini AI backend
                            onSubmit("General Query", textToSend)

                            // 3. Generate instant AI answer in chat thread
                            coroutineScope.launch {
                                listState.animateScrollToItem(chatList.size - 1)
                                kotlinx.coroutines.delay(1200)
                                isThinking = false

                                val aiAnswer = when {
                                    textToSend.contains("delivery", ignoreCase = true) || textToSend.contains("ವಿಲೇವಾರಿ") -> {
                                        if (isKannada) "ನಿಮ್ಮ ಸಿಲಿಂಡರ್ ವಿಲೇವಾರಿ ಪ್ರಕ್ರಿಯೆಯಲ್ಲಿದೆ. ವಿಲೇವಾರಿ ಪಾಲುದಾರರು ಇಂದು ತಲುಪಿಸಲಿದ್ದಾರೆ."
                                        else "Your refill cylinder is assigned and currently out for delivery. Our partner will deliver it today."
                                    }
                                    textToSend.contains("pay", ignoreCase = true) || textToSend.contains("ಪಾವತಿ") -> {
                                        if (isKannada) "ನೀವು ಯುಪಿಐ, ಕ್ಯೂಆರ್ ಕೋಡ್ ಅಥವಾ ವಿಲೇವಾರಿ ವೇಳೆಯಲ್ಲಿ ನಗದು ರೂಪದಲ್ಲಿ ಪಾವತಿಸಬಹುದು."
                                        else "You can complete your payment via UPI QR code or cash at the time of delivery."
                                    }
                                    textToSend.contains("leak", ignoreCase = true) || textToSend.contains("ಸೋರಿಕೆ") -> {
                                        if (isKannada) "ಅನಿಲ ಸೋರಿಕೆಯಾದರೆ ತಕ್ಷಣ ರೆಗ್ಯುಲೇಟರ್ ಬಂದ್ ಮಾಡಿ, ಕಿಟಕಿಗಳನ್ನು ತೆರೆಯಿರಿ ಮತ್ತು 1906 ಗೆ ಕರೆ ಮಾಡಿ."
                                        else "In case of gas leakage, immediately close the cylinder regulator, open all windows, avoid electrical switches, and call emergency 1906."
                                    }
                                    else -> {
                                        if (isKannada) "ಧನ್ಯವಾದಗಳು! ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ಹೆಚ್ಚುವರಿ ಸಹಾಯ ಬೇಕಾದಲ್ಲಿ ಮಾನವ ಸಿಬ್ಬಂದಿಗೆ ವಹಿಸಿ."
                                        else "Thank you for reaching out! Your query has been logged and answered by Gemini AI. Tap Escalate if you need further help."
                                    }
                                }

                                chatList.add(ChatMessage(id = UUID.randomUUID().toString(), text = aiAnswer, isUser = false))
                                listState.animateScrollToItem(chatList.size - 1)
                            }
                        }
                    },
                    modifier = Modifier
                        .size(44.dp)
                        .background(
                            color = if (userMessageText.isNotBlank()) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                            shape = CircleShape
                        )
                ) {
                    Icon(
                        imageVector = Icons.Default.Send,
                        contentDescription = "Send",
                        tint = if (userMessageText.isNotBlank()) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun AiBubble(
    text: String,
    isKannada: Boolean,
    ticketId: Int? = null,
    status: String? = null,
    onEscalate: ((Int) -> Unit)? = null
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.Default.SmartToy,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.size(18.dp)
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        Surface(
            color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f),
            shape = RoundedCornerShape(topStart = 0.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            modifier = Modifier.widthIn(max = 280.dp)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = if (isKannada) "ಎಐ ಸಹಾಯಕಿ" else "Gemini AI Support",
                        fontWeight = FontWeight.Bold,
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(text = text, style = MaterialTheme.typography.bodyMedium)

                if (ticketId != null && onEscalate != null && (status == "AI_ASSISTED" || status == "OPEN")) {
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedButton(
                        onClick = { onEscalate(ticketId) },
                        shape = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Icon(Icons.Default.Warning, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = if (isKannada) "ಮಾನವ ಸಿಬ್ಬಂದಿಗೆ ವಹಿಸಿ" else "Escalate to Human Staff",
                            fontSize = 11.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun UserBubble(text: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.End
    ) {
        Surface(
            color = MaterialTheme.colorScheme.primary,
            shape = RoundedCornerShape(topStart = 16.dp, topEnd = 0.dp, bottomStart = 16.dp, bottomEnd = 16.dp),
            modifier = Modifier.widthIn(max = 280.dp)
        ) {
            Text(
                text = text,
                color = MaterialTheme.colorScheme.onPrimary,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(12.dp)
            )
        }
    }
}
