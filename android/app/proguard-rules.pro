# NeuroArousal ProGuard rules
-keep class com.neuroarousal.api.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn okhttp3.**
-dontwarn retrofit2.**
