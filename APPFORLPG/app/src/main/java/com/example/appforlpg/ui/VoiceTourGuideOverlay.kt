package com.example.appforlpg.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.appforlpg.util.AudioGuidePlayer

data class TourStep(
    val audioId: String,
    val titleEn: String,
    val titleKn: String,
    val textEn: String,
    val textKn: String
)

val tourStepsList = listOf(
    TourStep(
        audioId = "tour_welcome",
        titleEn = "Welcome to LPG Smart ERP",
        titleKn = "ಎಲ್.ಪಿ.ಜಿ ಸ್ಮಾರ್ಟ್ ಈ.ಆರ್.ಪಿ ಆಪ್‌ಗೆ ಸುಸ್ವಾಗತ",
        textEn = "Welcome! Let us show you around the portal for quick cylinder bookings and delivery tracking.",
        textKn = "ಎಲ್.ಪಿ.ಜಿ ಸ್ಮಾರ್ಟ್ ಈ.ಆರ್.ಪಿ ಆಪ್‌ಗೆ ಸುಸ್ವಾಗತ! ಆಪ್ ಬಳಕೆಯ ಮಾರ್ಗದರ್ಶನ ಇಲ್ಲಿದೆ."
    ),
    TourStep(
        audioId = "tour_language",
        titleEn = "Bilingual Language Toggle",
        titleKn = "ದ್ವಿಭಾಷಾ ಆಯ್ಕೆ",
        textEn = "Tap the globe icon in the top header at any time to switch instantly between English and Kannada.",
        textKn = "ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡ ಭಾಷೆ ಬದಲಾಯಿಸಲು ಈ ಮೇಲಿನ ಬಟನ್ ಒತ್ತಿ."
    ),
    TourStep(
        audioId = "tour_booking",
        titleEn = "Refill Cylinder Booking",
        titleKn = "ಸಿಲಿಂಡರ್ ಕಾಯ್ದಿರಿಸುವಿಕೆ",
        textEn = "Select 14.2 kg Domestic or 19 kg Commercial cylinder, adjust quantity, and tap Book Cylinder Now.",
        textKn = "ನಿಮ್ಮ ಸಿಲಿಂಡರ್ ಪ್ರಕಾರ ಆಯ್ಕೆ ಮಾಡಿ, ಸಿಲಿಂಡರ್ ಕಾಯ್ದಿರಿಸಲು ಬಟನ್ ಒತ್ತಿ."
    ),
    TourStep(
        audioId = "tour_history",
        titleEn = "Activity & Delivery History",
        titleKn = "ಕಾಯ್ದಿರಿಸುವಿಕೆ ಇತಿಹಾಸ",
        textEn = "Track live delivery partner assignment, execution status, and payment collection receipts in real-time.",
        textKn = "ನಿಮ್ಮ ಕಾಯ್ದಿರಿಸುವಿಕೆ ಮತ್ತು ವಿಲೇವಾರಿ ಇತಿಹಾಸವನ್ನು ಇಲ್ಲಿ ಪರಿಶೀಲಿಸಿ."
    ),
    TourStep(
        audioId = "tour_support",
        titleEn = "Gemini AI Support & Issues",
        titleKn = "ಎಐ ಬೆಂಬಲ ಹಾಗೂ ಸಹಾಯ",
        textEn = "Need assistance? Chat directly with our 24/7 Gemini AI Assistant or escalate to human staff.",
        textKn = "ಸಹಾಯ ಬೇಕೇ? ನಮ್ಮ ಎಐ ಸಹಾಯಕರನ್ನು ಕೇಳಿ ಅಥವಾ ಬೆಂಬಲ ಪಡೆಯಿರಿ."
    ),
    TourStep(
        audioId = "tour_finish",
        titleEn = "Tour Complete!",
        titleKn = "ಮಾರ್ಗದರ್ಶನ ಪೂರ್ಣಗೊಂಡಿದೆ!",
        textEn = "You are all set to use LPG Smart ERP! Tap anytime to replay this voice guide.",
        textKn = "ನಿಮ್ಮ ಮಾರ್ಗದರ್ಶನ ಪೂರ್ಣಗೊಂಡಿದೆ! ಧನ್ಯವಾದಗಳು."
    )
)

@Composable
fun VoiceTourGuideOverlay(
    isKannada: Boolean,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val audioPlayer = remember { AudioGuidePlayer(context) }
    var currentStepIndex by remember { mutableStateOf(0) }
    var isMuted by remember { mutableStateOf(audioPlayer.isMuted) }

    val currentStep = tourStepsList[currentStepIndex]

    // Play narration on step change or language change
    LaunchedEffect(currentStepIndex, isKannada) {
        audioPlayer.play(currentStep.audioId, isKannada)
    }

    DisposableEffect(Unit) {
        onDispose {
            audioPlayer.release()
        }
    }

    AlertDialog(
        onDismissRequest = {
            audioPlayer.stop()
            onDismiss()
        },
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.HelpOutline,
                        contentDescription = "Voice Guide",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isKannada) currentStep.titleKn else currentStep.titleEn,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                IconButton(onClick = {
                    audioPlayer.stop()
                    onDismiss()
                }) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Close",
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                // Step Progress Indicator
                LinearProgressIndicator(
                    progress = { (currentStepIndex + 1).toFloat() / tourStepsList.size },
                    modifier = Modifier.fillMaxWidth().height(6.dp),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.primaryContainer
                )

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = if (isKannada) "ಹಂತ ${currentStepIndex + 1} / ${tourStepsList.size}" else "Step ${currentStepIndex + 1} of ${tourStepsList.size}",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.secondary
                )

                Spacer(modifier = Modifier.height(8.dp))

                // On-screen Caption
                Text(
                    text = if (isKannada) currentStep.textKn else currentStep.textEn,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Audio Controls (Replay & Mute)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedIconButton(
                        onClick = {
                            audioPlayer.play(currentStep.audioId, isKannada)
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Default.Replay,
                            contentDescription = "Replay Audio",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }

                    Spacer(modifier = Modifier.width(16.dp))

                    OutlinedIconButton(
                        onClick = {
                            isMuted = audioPlayer.toggleMute()
                        }
                    ) {
                        Icon(
                            imageVector = if (isMuted) Icons.Default.VolumeOff else Icons.Default.VolumeUp,
                            contentDescription = if (isMuted) "Unmute" else "Mute",
                            tint = if (isMuted) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (currentStepIndex < tourStepsList.size - 1) {
                        currentStepIndex++
                    } else {
                        audioPlayer.stop()
                        onDismiss()
                    }
                }
            ) {
                Text(
                    if (currentStepIndex < tourStepsList.size - 1) {
                        if (isKannada) "ಮುಂದೆ" else "Next"
                    } else {
                        if (isKannada) "ಪೂರ್ಣಗೊಳಿಸಿ" else "Finish"
                    }
                )
                Spacer(modifier = Modifier.width(4.dp))
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
            }
        },
        dismissButton = {
            if (currentStepIndex > 0) {
                OutlinedButton(
                    onClick = {
                        currentStepIndex--
                    }
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(if (isKannada) "ಹಿಂದೆ" else "Back")
                }
            }
        }
    )
}
