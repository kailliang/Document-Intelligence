declare module 'html2pdf.js' {
    interface Html2PdfOptions {
        margin?: number | [number, number, number, number];
        filename?: string;
        image?: { type?: string; quality?: number };
        html2canvas?: any;
        jsPDF?: any;
        pagebreak?: { mode?: string[] };
        enableLinks?: boolean;
        html2canvas?: {
            scale?: number;
            useCORS?: boolean;
            allowTaint?: boolean;
            backgroundColor?: string;
        };
        jsPDF?: {
            orientation?: 'portrait' | 'landscape';
            unit?: 'pt' | 'mm' | 'cm' | 'in';
            format?: string | [number, number];
        };
    }

    interface Html2PdfInstance {
        from(element: HTMLElement | string): Html2PdfInstance;
        set(options: Html2PdfOptions): Html2PdfInstance;
        save(): Promise<void>;
        toPdf(): Html2PdfInstance;
        toImg(): Html2PdfInstance;
        toContainer(): Html2PdfInstance;
        toCanvas(): Html2PdfInstance;
        outputPdf(): Html2PdfInstance;
        outputImg(): Html2PdfInstance;
        outputContainer(): Html2PdfInstance;
        outputCanvas(): Html2PdfInstance;
        then(callback: () => void): Html2PdfInstance;
        catch(callback: (error: any) => void): Html2PdfInstance;
    }

    function html2pdf(): Html2PdfInstance;
    function html2pdf(element: HTMLElement | string, options?: Html2PdfOptions): Html2PdfInstance;

    export = html2pdf;
} 